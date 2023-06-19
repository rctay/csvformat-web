import datetime
import io
import os
import sys
import tempfile
from csvkit import agate

from pathlib import PurePath
from flask import Flask, after_this_request, render_template, request, send_file

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

    (input_filedescriptor, input_filename) = tempfile.mkstemp()

    input_file = os.fdopen(input_filedescriptor, 'w+b')
    uploaded_file.save(input_file)
    input_file.close()

    (output_filedescriptor, output_filename) = tempfile.mkstemp()

    with open(input_filename) as input_file:
        with os.fdopen(output_filedescriptor, 'w+') as output_file:
            csvformat(
                input_file=input_file,
                output_file=output_file)

    @after_this_request
    def cleanup_temp_files(response):
        try:
            os.remove(output_filename)
            os.remove(input_filename)
        except Exception as error:
            app.logger.error("Error removing or closing downloaded file handle", error)
        return response

    return send_file(output_filename,
        mimetype='text/csv',
        as_attachment=True, download_name=get_output_filename(uploaded_file.filename)
    )


def csvformat(input_file, output_file):
    reader = agate.csv.reader(input_file, delimiter=';')
    writer = agate.csv.writer(output_file, delimiter=',')
    writer.writerows(reader)


def get_output_filename(input_filename):
    path = PurePath(input_filename)
    filename = path.name
    return path.stem + (path.suffix if path.suffix else '.csv')

if __name__ == "__main__":
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host="127.0.0.1", port=8080, debug=True)

