const express = require('express');
const bodyParser = require('body-parser');
var PythonShell = require('python-shell');
var cors = require('cors')

// create express app
const app = express();
app.use(cors());

// parse requests of content-type - application/x-www-form-urlencoded
app.use(bodyParser.urlencoded({ extended: true }))

// parse requests of content-type - application/json
app.use(bodyParser.json())

app.post('/getBoundingBoxes', (req, res) => {

console.log(req);
var str ={"status":"ok"};
res.send(str);

});

// define a simple route
app.post('/getRawImage', (req, res) => {

	var pyshell = new PythonShell("getRawImage.py");
	pyshell.on('message', function (message) {
  // received a message sent from the Python script (a simple "print" statement)
  //var jsonObject = {}; // empty Object
  //var jsonObject = JSON.parse(message);
  //jsonObject['RawImageBase64'] = [];
  var data={
  	"RawImageBase64":message
  	}
  //var json = jsonObject['RawImageBase64'].push(data);
  //var json1 = JSON.stringify(json);
  console.log(data);
  res.send(data);
});

	/*PythonShell.run('getRawImage.py', function (err) {
		if (err) throw err;
  		console.log('Taken raw image');
	});
	*/
    //res.json({"message": "Welcome to EasyNotes application. Take notes quickly. Organize and keep track of all your notes."});
	//res.send("Received the ping");
});

// listen for requests
app.listen(3000, () => {
    console.log("Server is listening on port 3000");
});

