function fill_schema(schema_name) {
  var xmlhttp = new XMLHttpRequest();
  xmlhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      var schema = JSON.parse(this.responseText);
      fields = schema.fields;
      var s = '<h3>' + schema_name + '</h3>';
      s += '<table class="table w-auto small">';
      for (var i=0; i < fields.length; i++) {
	s += "<tr><td>" + schema_name + "." + fields[i].name + '</td><td>' + fields[i].doc + '</td></tr>'
      }
      s += "</table>"
      document.getElementById("schema_" + schema_name).innerHTML = s;
    }
  };
  xmlhttp.open("GET", "/lasair/static/schema/" + schema_name + ".json", true);
  xmlhttp.send();
}

function showinfodiv(){
    if(document.getElementById('infodiv' ).style.display == 'block') {
        document.getElementById('infodiv' ).style.display = 'none'
    } else {
        document.getElementById('infodiv' ).style.display = 'block'
    }
}

/* respond to clicking a checkbox */
function puttext() {
  var boxes = document.getElementsByName('put');
  var nonobjects = 0;
  var text = '';
  var checked_wl = '';
  var checked_ar = '';
  for(i=0; i<boxes.length; i++){
    if(boxes[i].checked && boxes[i].id != 'objects'){
      nonobjects += 1;
    }
    if(boxes[i].checked && boxes[i].id == 'watchlist'){
      var radios = document.getElementsByName("wl");
      for (var j = 0; j < radios.length; j++) {
        if (radios[j].checked) {
          checked_wl = radios[j].value;
        }
      }
    }
    if(boxes[i].checked && boxes[i].id == 'area'){
      var radios = document.getElementsByName("ar");
      for (var j = 0; j < radios.length; j++) {
        if (radios[j].checked) {
          checked_ar = radios[j].value;
        }
      }
    }
  }
  if(nonobjects > 1){
    document.getElementById('objects').checked = true;
  }
  var nt = 0;
  for(i=0; i<boxes.length; i++){
    if(boxes[i].checked){
      if(nt > 0){
        text += ', '
      }
      if(boxes[i].id == 'watchlist'){
        if(checked_wl.length == 0){
          continue;
	} else {
          text += 'watchlist:' + checked_wl;
        }
      }
      else if(boxes[i].id == 'area'){
        if(checked_ar.length == 0){
          continue;
	} else {
          text += 'area:' + checked_ar;
        }
      }
      else {
        text += boxes[i].id;
      }
      nt += 1;
    }
  }
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
