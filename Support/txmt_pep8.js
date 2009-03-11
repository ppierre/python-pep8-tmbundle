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

function load_from_cookie(name) {
  console.log(document.cookie);
  var cookie = document.cookie;
  if (cookie && cookie.length > (name.length + 2)) {
    var i_code = cookie.indexOf(name + '=');
    var view_source = parseInt(cookie.substring(
              i_code + name.length + 1, i_code + name.length + 2), 10);
    toggle(name, view_source);
    document.getElementById(name).checked = view_source;
  }
}

window.onload = function () {
  load_from_cookie('view_source');
  load_from_cookie('view_pep');
  save_cookie();
};
