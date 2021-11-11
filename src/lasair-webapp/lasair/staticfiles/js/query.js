function fill_schema(schema_name, display_name) {
  var xmlhttp = new XMLHttpRequest();
  xmlhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      var schema = JSON.parse(this.responseText);
      fields = schema.fields;
      var s = '<h4><a href="#" onclick="showdiv(' + "'table_" + schema_name + "'" + ');">' + schema_name + '</a></h4>';
      s += '<div id="table_' + schema_name + '" style="display:none">';
      s += '<table class="table w-auto small">';
      for (var i=0; i < fields.length; i++) {
	s += "<tr><td>" + display_name + "." + fields[i].name + '</td><td>' + fields[i].doc + '</td></tr>'
      }
      s += "</table></div>"
      document.getElementById("schema_" + schema_name).innerHTML = s;
    }
  };
  xmlhttp.open("GET", "/lasair/static/schema/" + schema_name + ".json", true);
  xmlhttp.send();
}

function showdiv(divid){
    if(document.getElementById(divid).style.display == 'block') {
        document.getElementById(divid).style.display = 'none'
    } else {
        document.getElementById(divid).style.display = 'block'
    }
}

/* respond to clicking a checkbox */
function puttext() {
  var boxes = document.getElementsByName('put');
  var fields = ['objects'];
  var checked_wl = '';
  var checked_ar = '';
  var checked_an = [];
  document.getElementById('objects').checked = true;

  for(i=0; i<boxes.length; i++){
    if(boxes[i].checked && boxes[i].id == 'sherlock_classifications'){
      fields.push('sherlock_classifications');
    }
    if(boxes[i].checked && boxes[i].id == 'crossmatch_tns'){
      fields.push('crossmatch_tns');
    }
    if(boxes[i].checked && boxes[i].id == 'watchlist'){
      var radios = document.getElementsByName("wl");
      for (var j = 0; j < radios.length; j++) {
        if (radios[j].checked) {
          fields.push('watchlist:' + radios[j].value);
        }
      }
    }
    if(boxes[i].checked && boxes[i].id == 'area'){
      var radios = document.getElementsByName("ar");
      for (var j = 0; j < radios.length; j++) {
        if (radios[j].checked) {
          fields.push('area:' + radios[j].value);
        }
      }
    }
    if(boxes[i].checked && boxes[i].id == 'annotator'){
      var radios = document.getElementsByName("an");
      for (var j = 0; j < radios.length; j++) {
        if (radios[j].checked) {
          fields.push('annotator:' + radios[j].value);
        }
      }
    }
  }
  text = fields.join(', ')
  console.log(text);
  document.getElementById("tables").value = text;
}

/* take the table text and fill in the checkboxes */
function check_boxes() {
  var tables = document.getElementById("tables").value;
	console.log(tables);
  var boxes = document.getElementsByName('put');
  for(i=0; i<boxes.length; i++){
    if(tables.indexOf(boxes[i].id) != -1){
      boxes[i].checked = true;
    }
  }
  var radios = document.getElementsByName("wl");
  document.getElementById('watchlistradios' ).style.display = 'none';
  for (var j = 0; j < radios.length; j++) {
    if (tables.indexOf('watchlist:' + radios[j].value) != -1) {
      radios[j].checked = true;
      document.getElementById('watchlistradios' ).style.display = 'block';
    }
  }
  var radios = document.getElementsByName("ar");
  document.getElementById('arearadios' ).style.display = 'none';
  for (var j = 0; j < radios.length; j++) {
    if (tables.indexOf('area:' + radios[j].value) != -1) {
      radios[j].checked = true;
      document.getElementById('arearadios' ).style.display = 'block';
    }
  }
  var radios = document.getElementsByName("an");
  document.getElementById('annotatorradios' ).style.display = 'none';
  for (var j = 0; j < radios.length; j++) {
    if (tables.indexOf('annotator:' + radios[j].value) != -1) {
      radios[j].checked = true;
      document.getElementById('annotatorradios' ).style.display = 'block';
    }
  }
}

function showwatchlistradiolist(){
    if(document.getElementById('watchlist' ).checked){
        document.getElementById('watchlistradios' ).style.display = 'block';
    } else {
        document.getElementById('watchlistradios' ).style.display = 'none';
    }
}
function showarearadiolist(){
    if(document.getElementById('area' ).checked){
        document.getElementById('arearadios' ).style.display = 'block';
    } else {
        document.getElementById('arearadios' ).style.display = 'none';
    }
}
function showannotatorradiolist(){
    if(document.getElementById('annotator' ).checked){
        document.getElementById('annotatorradios' ).style.display = 'block';
    } else {
        document.getElementById('annotatorradios' ).style.display = 'none';
    }
}
