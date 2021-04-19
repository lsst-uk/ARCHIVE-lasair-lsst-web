import os
from django.shortcuts import render, get_object_or_404, redirect
from django.template.context_processors import csrf
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth.models import User
import lasair.settings
from lasair.models import Myqueries
from lasair.models import Watchlists, Areas
from lasair.query_builder import check_query, build_query
from lasair.topic_name import topic_name
import utility.date_nid as date_nid
from datetime import datetime, timedelta
import mysql.connector
import string, random, json

def connect_db():
    """connect_db.
    """
    msl = mysql.connector.connect(
        user    =lasair.settings.READONLY_USER,
        password=lasair.settings.READONLY_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        database='ztf')
    return msl

def check_query_zero_limit(real_sql):
    msl = connect_db()
    cursor = msl.cursor(buffered=True, dictionary=True)

    try:
        cursor.execute(real_sql + ' LIMIT 0')
        return None
    except Exception as e:
        message = 'Your query:<br/><b>' + real_sql + '</b><br/>returned the error<br/><i>' + str(e) + '</i>'
        return message

def query_list(qs):
    """query_list.

    Args:
        qs:
    """
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
            topic = topic_name(q.user.id, q.name)
            d['streamlink'] = '/streams/%s' % topic
        list.append(d)
    return list

def querylist(request):
    """querylist.

    Args:
        request:
    """
    # shows the list of queries
    promoted_queries = Myqueries.objects.filter(public=2)

    public_queries = Myqueries.objects.filter(public__gte=1)

    if request.user.is_authenticated:
        myqueries    = Myqueries.objects.filter(user=request.user)
    else:
        myqueries    = None

    if request.user.is_authenticated:
        watchlists = Watchlists.objects.filter(Q(user=request.user) | Q(public__gte=1))
        areas      =      Areas.objects.filter(Q(user=request.user) | Q(public__gte=1))
    else:
        watchlists = Watchlists.objects.filter(public__gte=1)
        areas      =      Areas.objects.filter(public__gte=1)

    return render(request, 'querylist.html', {
        'promoted_queries' : query_list(promoted_queries),
        'is_authenticated' : request.user.is_authenticated,
        'myqueries'        : query_list(myqueries), 
        'watchlists'       : watchlists,
        'areas'            : areas,
        'public_queries'   : query_list(public_queries)
    })

def new_myquery(request):
    """new_myquery.

    Args:
        request:
    """
    return handle_myquery(request)

def show_myquery(request, mq_id):
    """show_myquery.

    Args:
        request:
        mq_id:
    """
    return handle_myquery(request, mq_id)

def delete_stream_file(request, query_name):
    topic = topic_name(request.user.id, query_name)
    filename = '/mnt/cephfs/roy/streams/%s' % topic
    if os.path.exists(filename):
        os.remove(filename)

def handle_myquery(request, mq_id=None):
    """handle_myquery.

    Args:
        request:
        mq_id:
    """
    logged_in = request.user.is_authenticated
    message = ''

    if logged_in:
        email = request.user.email
        watchlists = Watchlists.objects.filter(Q(user=request.user) | Q(public__gte=1))
        areas      =      Areas.objects.filter(Q(user=request.user) | Q(public__gte=1))
    else:
        email = ''
        watchlists = Watchlists.objects.filter(public__gte=1)
        areas      =      Areas.objects.filter(public__gte=1)

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
            if public == 'on': 
                public = 1
            else:
                public = 0

            e = check_query(selected, tables, conditions)
            if e:
                return render(request, 'error.html', {'message': e})

            sqlquery_real = build_query(selected, tables, conditions)
            e = check_query_zero_limit(real_sql)
            if e:
                return render(request, 'error.html', {'message': e})

            tn = topic_name(request.user.id, name)

            myquery = Myqueries(user=request.user, 
                    name=name, description=description,
                    public=public, active=active, 
                    selected=selected, conditions=conditions, tables=tables,
                    real_sql=sqlquery_real, topic_name=tn)
            myquery.save()
            message += "Query saved successfully"
            return render(request, 'queryform.html',{
                'myquery'   : myquery,
                'watchlists': watchlists,
                'areas'     : areas,
                'is_owner'  : True,
                'logged_in' : logged_in,
                'new'       : False,
                'message'   : message})
        else:
            # New query, blank query form
            return render(request, 'queryform.html',{
                'watchlists': watchlists,
                'areas'     : areas,
                'random'    : '%d'%random.randrange(1000),
                'email'     : email,
                'is_owner'  : True,
                'logged_in' : logged_in,
                'new'       : True,
                'message'   : 'New query'
            })

    # Existing query
    myquery = get_object_or_404(Myqueries, mq_id=mq_id)
    is_owner = logged_in and (request.user == myquery.user)

    if not is_owner and myquery.public==0:
        return render(request, 'error.html', {'message': 'This query is private'})

    # Existing query, owner wants to change it
    if request.method == 'POST' and logged_in:

        # Delete the given query
        if 'delete' in request.POST:
            myquery.delete()
            delete_stream_file(request, myquery.name)
            return redirect('/querylist/')

        # Copy the given query
        if 'copy' in request.POST:
            newname = 'Copy_Of_' + myquery.name + '_'
            letters = string.ascii_lowercase
            newname += ''.join(random.choice(letters) for i in range(6))
            tn = topic_name(request.user.id, newname)
            mq = Myqueries(user=request.user, name=newname, 
                    description=myquery.description,
                    public=0, active=0, 
                    selected=myquery.selected, 
                    conditions=myquery.conditions, tables=myquery.tables,
                    real_sql=myquery.real_sql, topic_name=tn)
            mq.save()
            message += 'Query copied'
            return redirect('/query/%d/' % mq.mq_id)

        # Update the given query from the post
        else:
            myquery.name         = request.POST.get('name')
            myquery.description  = request.POST.get('description')
            myquery.selected     = request.POST.get('selected')
            myquery.tables       = request.POST.get('tables')
            myquery.conditions   = request.POST.get('conditions')
            public               = request.POST.get('public')
            e = check_query(myquery.selected, myquery.tables, myquery.conditions)
            if e:
                return render(request, 'error.html', {'message': e})

            myquery.real_sql = build_query(myquery.selected, myquery.tables, myquery.conditions)
            e = check_query_zero_limit(myquery.real_sql)
            if e:
                return render(request, 'error.html', {'message': e})

            tn = topic_name(request.user.id, myquery.name)
            myquery.topic_name = tn
            try:
                myquery.active   = int(request.POST.get('active'))
            except:
                myquery.active = 0

            if public == 'on':
                if myquery.public is None or myquery.public == 0:
                    myquery.public  = 1 # if set to 1 or 2 leave it as it is
            else:
                myquery.public  = 0
            delete_stream_file(request, myquery.name)
            message += 'Query updated: %s' % myquery.name

        myquery.save()
        return render(request, 'queryform.html',{
            'myquery'   : myquery,
            'watchlists': watchlists,
            'areas'     : areas,
            'is_owner'  : is_owner,
            'logged_in' : logged_in,
            'new'       : False,
            'message'   : message})

    # Existing query, view it 
    message = 'Query displayed'
    return render(request, 'queryform.html',{
        'myquery'   : myquery,
        'watchlists': watchlists,
        'areas'     : areas,
        'is_owner'  : is_owner,
        'logged_in' : logged_in,
        'new'       : False,
        'message'   : message})


def record_query(request, query):
    """record_query.

    Args:
        request:
        query:
    """
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
    """runquery.

    Args:
        request:
    """
    message = ''
    json_checked = False

    if not request.method == 'POST':
        return render(request, 'error.html', {'message': 'This code expects a POST'})

    selected   = request.POST['selected'].strip()
    tables     = request.POST['tables'].strip()
    conditions = request.POST['conditions'].strip()

    limit = 1000
    if 'limit' in request.POST:
        limit      = request.POST['limit']
        try:
            limit = int(limit)
        except:
            return render(request, 'error.html', {'message': 'LIMIT must be an integer'})
        if limit > 1000:
            return render(request, 'error.html', {'message': 'LIMIT must be 1000 or less'})

    offset = 0
    if 'offset' in request.POST:
        offset     = request.POST['offset']
        try:
            offset = int(offset)
        except:
            return render(request, 'error.html', {'message': 'OFFSET must be an integer'})

    if 'json' in request.POST and request.POST['json'] == 'on':
        json_checked = True


#    sqlquery_real = query_utilities.make_query(selected, tables, conditions, limit, offset)

    e = check_query(selected, tables, conditions)
    if e:
        return render(request, 'error.html', {'message': message})
    sqlquery_real = build_query(selected, tables, conditions)
    sqlquery_limit = sqlquery_real + ' LIMIT %d OFFSET %d' % (limit, offset)
    message += sqlquery_limit

# lets keep a record of all the queries the people try to execute
#    record_query(request, sqlquery_real)

    nalert = 0
    msl = connect_db()
    cursor = msl.cursor(buffered=True, dictionary=True)

    try:
        cursor.execute(sqlquery_limit)
    except Exception as e:
        message = 'Your query:<br/><b>' + sqlquery_limit + '</b><br/>returned the error<br/><i>' + str(e) + '</i>'
        return render(request, 'error.html', {'message': message})

    queryset = []
    for row in cursor:
        queryset.append(row)
        nalert += 1

    if json_checked:
        return HttpResponse(json.dumps(queryset, indent=2), content_type="application/json")
    else:
        return render(request, 'runquery.html',
            {'table': queryset, 'nalert': nalert, 
                'selected'  :selected, 
                'tables'    :tables, 
                'conditions'  :conditions, 
                'limit'  :limit, 'offset'  :offset, 
                'message': message})
