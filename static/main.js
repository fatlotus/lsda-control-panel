(function() {
  "use strict";
  
  var makePath = function(points) {
    var WIDTH = 300;
    var HEIGHT = 50;
  
    var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    var instructions = ["M 0 " + HEIGHT];
  
    for (var i = 0; i < points.length; i++) {
      var x = Math.floor((i - 1) / parseFloat(points.length - 3) * WIDTH)
        + 0.5;
      var y = Math.floor((1 - points[i]) * HEIGHT) + 0.5;
    
      instructions.push("L " + x + " " + y);
    }
  
    instructions.push("L " + (WIDTH + 1) + " " + HEIGHT);
  
    path.setAttribute("d", instructions.join(" "));
  
    return path;
  }

  var renderCPUData = function(data) {
    console.log(data);
    
    var graphParent = document.getElementById("graph");
  
    while (graphParent.hasChildNodes())
      graphParent.removeChild(graphParent.firstChild);
  
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    var maxInstances = 0;
  
    for (var i = 0; i < data['instances'].length; i++)
      if (data['instances'][i] > maxInstances)
        maxInstances = data['instances'][i];
  
    var used = [];
  
    for (var i = 0; i < data['cpu_utilization'].length; i++) {
      var fraction = data['cpu_utilization'][i] / 100.0;
      var cores = fraction * data['instances'][Math.floor(
        i * data['cpu_utilization'].length / data['instances'].length)];
      used.push(cores / maxInstances);
    }
  
    var limit = [];
    for (var i = 0; i < data['instances'].length; i++)
      limit.push(data['instances'][i] / maxInstances);
  
    svg.setAttribute("viewBox", "0 0 300 50");
    svg.style.width = "300px";
    svg.style.height = "50px";
  
    var usedPath = makePath(used);
    var limitPath = makePath(limit);
    var value = document.createElement("p");
  
    usedPath.setAttribute("fill", "#eee");
    usedPath.setAttribute("stroke", "#000");
    usedPath.setAttribute("stroke-width", "1");
  
    limitPath.setAttribute("fill", "#fff");
    limitPath.setAttribute("stroke", "#ccc");
    limitPath.setAttribute("stroke-width", "1");
  
    var span = document.createElement("em");
    span.innerText = ((data['cpu_utilization'][
      data['cpu_utilization'].length - 1]) / 100 * (data['instances'][
      data['instances'].length - 1])).toFixed(1);
  
    var label = document.createElement("span");
    label.innerText = "cores";
  
    value.appendChild(span);
    value.appendChild(label);
  
    svg.appendChild(limitPath);
    svg.appendChild(usedPath);
    graphParent.appendChild(value);
    graphParent.appendChild(svg);
  }
  
  var renderCommitList = function(commits) {
    var parent = document.getElementById('commits');
    
    while (parent.hasChildNodes())
      parent.removeChild(parent.firstChild);
    
    for (var i = 0; i < commits.length; i++) {
      var commit = document.createElement('blockquote');
      var p = document.createElement('p');
      p.innerText = commits[i].message;
      
      var author = document.createElement('cite');
      author.innerText = commits[i].committer;
      
      commit.appendChild(p);
      commit.appendChild(author);
      parent.appendChild(commit);
    }
  }
  
  var updateData = function() {
    var xhr = new XMLHttpRequest;
    xhr.open("GET", "/data", true);
    xhr.onreadystatechange = function() {
      if (xhr.readyState == 4) {
        renderCPUData(JSON.parse(xhr.responseText));
      }
    }
    xhr.send(null);
    
    var xhr2 = new XMLHttpRequest;
    xhr2.open("GET", "/commits", true);
    xhr2.onreadystatechange = function() {
      if (xhr2.readyState == 4) {
        renderCommitList(JSON.parse(xhr2.responseText).commits);
      }
    }
    xhr2.send(null);
  }

  window.addEventListener("load", function() {
    updateData();
  });

})();