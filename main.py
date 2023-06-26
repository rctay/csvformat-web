import datetime
import io
from csvkit import agate

from pathlib import PurePath
from flask import Flask, render_template, request, redirect, send_file

app = Flask(__name__)


@app.route("/")
def root():
    # For the sake of example, use static information to inflate the template.
    # This will be replaced with real information in later steps.
    dummy_times = [
        datetime.datetime(2018, 1, 1, 10, 0, 0),
        datetime.datetime(2018, 1, 2, 10, 30, 0),
        datetime.datetime(2018, 1, 3, 11, 0, 0),
    ]

    return render_template("index.html", times=dummy_times)

@app.route("/convert", methods=['POST'])
def convert():
    if 'file' not in request.files:
        return redirect('/')

    uploaded_file = request.files['file']

    if uploaded_file.filename == '':
        return redirect('/')

    output_file = io.StringIO()

    with io.TextIOWrapper(uploaded_file) as input_file:
        csvformat(
            input_file=input_file,
            output_file=output_file)

    return send_file(io.BytesIO(output_file.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True, download_name=get_output_filename(uploaded_file.filename)
    )


def csvformat(input_file, output_file):
    reader = agate.csv.reader(input_file, delimiter=';')
    writer = agate.csv.writer(output_file, delimiter=',')
    writer.writerows(reader)


def get_output_filename(input_filename):
    path = PurePath(input_filename)
    new_stem = path.stem + "_comma"
    extension = path.suffix if path.suffix else '.csv'
    return new_stem + extension

if __name__ == "__main__":
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host="127.0.0.1", port=8080, debug=True)

