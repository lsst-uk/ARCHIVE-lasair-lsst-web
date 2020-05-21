from django.shortcuts import render, get_object_or_404, redirect
from django.template.context_processors import csrf
from django.db import connection
from django.db.models import Q
from django.contrib.auth.models import User
import lasair.settings
from lasair.models import Myqueries
from lasair.models import Watchlists
from utility import query_utilities
import utility.date_nid as date_nid
from datetime import datetime, timedelta
import mysql.connector

def connect_db():
    msl = mysql.connector.connect(
        user    =lasair.settings.READONLY_USER,
        password=lasair.settings.READONLY_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        database='ztf')
    return msl

def query_list(qs):
    # takes the list of queries and adds a strealink for each one
    list = []
    if not qs:
        return list
    for q in qs:
        d = {
            'mq_id'      :q.mq_id,
            'usersname'  :q.user.first_name +' '+ q.user.last_name,
            'selected'   :q.selected,
            'tables'     :q.tables,
            'conditions' :q.conditions,
            'name'       :q.name,
            'active'     :q.active,
            'public'     :q.public,
            'description':q.description
        }
        d['streamlink'] = 'inactive'
        if q.active:
            topic = query_utilities.topic_name(q.user.id, q.name)
            d['streamlink'] = '/streamlog/%s' % topic
        list.append(d)
    return list

def querylist(request):
    # shows the list of queries
    promoted_queries = Myqueries.objects.filter(public=2)

    public_queries = Myqueries.objects.filter(public__gte=1)

    if request.user.is_authenticated:
        myqueries    = Myqueries.objects.filter(user=request.user)
    else:
        myqueries    = None

    if request.user.is_authenticated:
        watchlists = Watchlists.objects.filter(Q(user=request.user) | Q(public__gte=1))
    else:
        watchlists = Watchlists.objects.filter(public__gte=1)

    return render(request, 'querylist.html', {
        'promoted_queries' : query_list(promoted_queries),
        'is_authenticated' : request.user.is_authenticated,
        'myqueries'        : query_list(myqueries), 
        'watchlists'       : watchlists,
        'days_ago'         : 1, 
        'public_queries'   : query_list(public_queries)
    })

def new_myquery(request):
    return handle_myquery(request)

def show_myquery(request, mq_id):
    return handle_myquery(request, mq_id)

def handle_myquery(request, mq_id=None):
    logged_in = request.user.is_authenticated

    if logged_in:
        email = request.user.email
        watchlists = Watchlists.objects.filter(Q(user=request.user) | Q(public__gte=1))
    else:
        email = ''
        watchlists = Watchlists.objects.filter(public__gte=1)

    if mq_id is None:
        # New query, returned from form
        if request.method == 'POST' and logged_in:
            name        = request.POST.get('name')
            description = request.POST.get('description')
            selected    = request.POST.get('selected')
            conditions  = request.POST.get('conditions')
            tables      = request.POST.get('tables')
            try:
                active  = int(request.POST.get('active'))
            except:
                active = 0
            public      = request.POST.get('public')

            myquery = Myqueries(user=request.user, name=name, description=description,
                public=public, active=active, selected=selected, conditions=conditions, tables=tables)
            myquery.save()
            message = "Query saved successfully"
            return render(request, 'queryform.html',{
                'myquery'   : myquery,
                'watchlists': watchlists,
                'is_owner'  : True,
                'logged_in' : logged_in,
                'new'       : False,
                'message'   : message})
        else:
            # New query, blank query form
            return render(request, 'queryform.html',{
                'watchlists': watchlists,
                'email'     : email,
                'is_owner'  : True,
                'logged_in' : logged_in,
                'new'       : True,
                'message'   : 'New query'
            })

    # Existing query
    myquery = get_object_or_404(Myqueries, mq_id=mq_id)
    is_owner = logged_in and (request.user == myquery.user)

    # Existing query, owner wants to change it
    if request.method == 'POST' and logged_in:

        # Delete the given query
        if 'delete' in request.POST:
            myquery.delete()
            return redirect('/querylist/')

        # Copy the given query
        if 'copy' in request.POST:
            mq = Myqueries(user=request.user, name='Copy Of ' + myquery.name, 
                    description=myquery.description,
                    public=0, active=0, 
                    selected=myquery.selected, 
                    conditions=myquery.conditions, tables=myquery.tables)
            myquery = mq
            message = 'Query copied'

        # Update the given query from the post
        else:
            myquery.name         = request.POST.get('name')
            myquery.description  = request.POST.get('description')
            myquery.selected     = request.POST.get('selected')
            myquery.tables       = request.POST.get('tables')
            myquery.conditions   = request.POST.get('conditions')
            public               = request.POST.get('public')
            try:
                myquery.active   = int(request.POST.get('active'))
            except:
                myquery.active = 0

            if public:
                if myquery.public == 0:
                    myquery.public  = 1 # if set to 1 or 2 leave it as it is
            else:
                myquery.public  = 0
            message = 'Query updated'

        myquery.save()
        return render(request, 'queryform.html',{
            'myquery'   : myquery,
            'watchlists': watchlists,
            'is_owner'  : is_owner,
            'logged_in' : logged_in,
            'new'       : False,
            'message'   : message})

    # Existing query, view it 
    message = 'Query displayed'
    return render(request, 'queryform.html',{
        'myquery'   : myquery,
        'watchlists': watchlists,
        'is_owner'  : is_owner,
        'logged_in' : logged_in,
        'new'       : False,
        'message'   : message})


def record_query(request, query):
    onelinequery = query.replace('\r', ' ').replace('\n', ' ')
    time = datetime.now().replace(microsecond=0).isoformat()

    if request.user.is_authenticated:
        name = request.user.first_name +' '+ request.user.last_name
    else:
        name = 'anonymous'

    IP       = request.META.get('REMOTE_ADDR')
    if 'HTTP_X_FORWARDED_FOR' in request.META:
        IP = record.request.META['HTTP_X_FORWARDED_FOR']

    date = date_nid.nid_to_date(date_nid.nid_now())
    filename = lasair.settings.QUERY_CACHE + '/' + date
    f = open(filename, 'a')
    s = '%s| %s| %s| %s\n' % (IP, name, time, onelinequery)
    f.write(s)
    f.close()

def runquery(request):
    return handle_runquery(request)

def runquery_stored(request, mq_id):
    return handle_runquery(request, mq_id)

def handle_runquery(request, mq_id=None):
    perpage = 1000
    message = ''
    json_checked = False

    if not mq_id is None:
        myquery = get_object_or_404(Myqueries, mq_id=mq_id)
        selected   = myquery.selected
        tables     = myquery.tables
        conditions = myquery.conditions
        page       = 0

    # if this is a POST request we need to process the form data
    elif request.method == 'POST':
        selected   = request.POST['selected'].strip()
        tables     = request.POST['tables'].strip()
        conditions = request.POST['conditions'].strip()
        page     = request.POST['page']
        if len(page.strip()) == 0: page = 0
        else:                      page = int(page)

        if 'json' in request.POST and request.POST['json'] == 'on':
            json_checked = True

    check_days_ago = False
    days_ago = 3000
    if 'check_days_ago' in request.POST and request.POST['check_days_ago'] == 'on':
        try:
            days_ago = float(request.POST['days_ago'])
            check_days_ago = True
        except:
            pass

    ps = page    *perpage
    pe = (page+1)*perpage

    sqlquery_real = query_utilities.make_query(selected, tables, conditions, \
            page, perpage, check_days_ago, days_ago, days_ago)
    message += sqlquery_real

# lets keep a record of all the queries the people try to execute
#    record_query(request, sqlquery_real)

    nalert = 0
    msl = connect_db()
    cursor = msl.cursor(buffered=True, dictionary=True)

    try:
        cursor.execute(sqlquery_real)
    except Exception as e:
        message = 'Your query:<br/><b>' + sqlquery_real + '</b><br/>returned the error<br/><i>' + str(e) + '</i>'
        return render(request, 'error.html', {'message': message})

    queryset = []
    for row in cursor:
        queryset.append(row)
        nalert += 1
    lastpage = 0
    if ps + nalert < pe:
        pe = ps + nalert
        lastpage = 1

    if json_checked:
        return HttpResponse(json.dumps(queryset), content_type="application/json")
    else:
        return render(request, 'runquery.html',
            {'table': queryset, 'nalert': nalert, 'nextpage': page+1, 'ps':ps, 'pe':pe, 
                'selected'  :selected, 
                'tables'    :tables, 
                'conditions'  :conditions, 
                'message': message, 'lastpage':lastpage})
