# Lab 03 - Build a WebApp

In lab 02, we built a Pulumi program that uses the Pulumi CLI to provision resources. This is the most common mechanism of interacting with Pulumi.

However, it's possible to provision Pulumi programs via other user interfaces. In this lab, we're going to build the skeleton of a web application which can be used to deploy Pulumi programs.

## Step 1 - Install Flask

We'll be using Flask to build our Web Application, so let's install it

```bash
# activate our virtualenv
source venv/bin/activate
pip3 install flask
```

## Step 2 - Update your `__main__.py`

Previously, the `__main__.py` file was being read by our Pulumi CLI. Let's instead turn it into a flask program.

Clear all the code you had in your `__main__.py` and add the following:

```python
import flask

app = flask.Flask(__name__)

app.secret_key = "super-secret-key"

@app.route("/ping", methods=["GET"])
def ping():
	return flask.jsonify("pong!", 200)
```

We're making a very barebones flask webserver here, with a single route: `/ping`.

We can now run this using python:

```python
venv/bin/python3 __main__.py
```

## Step 3 - Create a root/index Page

Now, we can start building the functionality of our web application. The Git repo you cloned already has all of the HTML and styling prepared,
we just need to add the routes into Flask.

Let's start by adding the root URI, `/`. Before that, we'll need to add some dependencies. Add the following lines of code to your `__main__.py`:

```python
import pulumi
from pulumi.x import automation as auto
from app import ProductionAppArgs, ProductionApp

project_name = "deployment-platyform"

def create_pulumi_program(name: str, image: str):
	app = ProductionApp(
		name, ProductionAppArgs(image="gcr.io/kuar-demo/kuard-amd64:blue")
	)

@app.route("/", methods=["GET"])
def list_deployments():
	deployments = []
	try:
		ws = auto.LocalWorkspace(project_settings=auto.ProjectSettings(name=project_name, runtime="python"))
		all_stacks = ws.list_stacks()
		for stack in all_stacks:
			stack = auto.select_stack(stack_name=stack.name,
			                          project_name=project_name,
			                          # no-op program, just to get outputs
			                          program=lambda: None)
			outs = stack.outputs()
			deployments.append({"name": stack.name, "url": outs["url"].value})
	except Exception as exn:
		flask.flash(str(exn), category="danger")
	return flask.render_template("index.html", deployments=deployments)
```

_At this stage, your `__main__.py` file should look like this_:

```python

```

## Step 4 - Add the `/new` page

We've added the page that lists all current deployments, but we don't actually have any deployments to list.

Let's add a page to create a new deployment.

Add the following to your `__main__.py`


```python
@app.route("/new", methods=["GET", "POST"])
def create_deployment():
    """creates new deployment"""
    if flask.request.method == "POST":
        stack_name = flask.request.form.get("name")
        image = flask.request.form.get("image")

        def pulumi_program():
            return create_pulumi_program(stack_name, image)

        try:
            # create a new stack, generating our pulumi program on the fly from the POST body
            stack = auto.create_stack(
                stack_name=str(stack_name),
                project_name=project_name,
                program=pulumi_program,
            )
            # deploy the stack, tailing the logs to stdout
            stack.up(on_output=print)
            flask.flash(f"Successfully created deployment '{stack_name}'", category="success")
        except auto.StackAlreadyExistsError:
            flask.flash(
                f"Error: Deployment with name '{stack_name}' already exists, pick a unique name",
                category="danger",
            )

        return flask.redirect(flask.url_for("list_deployments"))

    return flask.render_template("create.html")
```

# Step 5 - Add a delete deployment page

Finally, we ened to be able to delete our deployments. Let's add a `/delete` page. Add the following to your `__main__.py`:

```python
@app.route("/<string:id>/delete", methods=["POST"])
def delete_deployment(id: str):
    stack_name = id
    try:
        stack = auto.select_stack(stack_name=stack_name,
                                  project_name=project_name,
                                  # noop program for destroy
                                  program=lambda: None)
        stack.destroy(on_output=print)
        stack.workspace.remove_stack(stack_name)
        flask.flash(f"Deployment '{stack_name}' successfully deleted!", category="success")
    except auto.ConcurrentUpdateError:
        flask.flash(f"Error: Deployment '{stack_name}' already has update in progress", category="danger")
    except Exception as exn:
        flask.flash(str(exn), category="danger")

    return flask.redirect(flask.url_for("list_deployments"))
```
