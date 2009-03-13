/*global XPathResult*/

function toggle(name, val) {
  var results = document.evaluate(
    "//*[@class='" + name + "']", 
    document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
  for (var i = 0; i < results.snapshotLength; i += 1) {
    var result = results.snapshotItem(i);
    if (val) {
      result.style.display = "block";
    } else {
      result.style.display = "none";
    }
  }
}

function save_cookie(id) {
  var cookie = "";
  cookie += id + "=";
  if (document.getElementById(id).checked) {
    cookie += "1";
  } else {
    cookie += "0";
  }
  cookie += ";";
  var d = new Date();
  d.setTime(d.getTime() + 1e10);
  document.cookie = cookie + 'expires=' + d.toGMTString();
}

function view(el) {
  toggle(el.id, el.checked);
  save_cookie('view_source');
  save_cookie('view_pep');
}

function read_cookie(name) {
  var cookie = document.cookie;
  if (cookie && cookie.length > (name.length + 2)) {
    var i_code = cookie.indexOf(name + '=');
    var view_source = parseInt(cookie.substring(
              i_code + name.length + 1, i_code + name.length + 2), 10);
    return view_source;
  }
}

function load_from_cookie(name) {
  var view_source = read_cookie(name);
  toggle(name, view_source);
  document.getElementById(name).checked = view_source;
}

window.onload = function () {
  load_from_cookie('view_source');
  load_from_cookie('view_pep');
  save_cookie('view_source');
  save_cookie('view_pep');
};

function write_style_for(name) {
  document.write("\n." + name + "{ display:");
  if (read_cookie(name)) {
    document.write("block;}");
  } else {
    document.write("none;}");
  }
}

// add styles to hide/show block before adding them
document.write("<style>");
write_style_for('view_source');
write_style_for('view_pep');
document.write("</style>");