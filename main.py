import datetime
import io
from csvkit import agate
import sys

from pathlib import PurePath
from flask import Flask, render_template, request, redirect, Response, send_file

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
        (input_kwargs, err) = infer_input(request.form['delimiter'], input_file)

        if err:
            return err

        csvformat(
            input_file=input_file,
            input_kwargs=input_kwargs,
            output_file=output_file)

    def get_output_filename(input_filename):
        path = PurePath(input_filename)
        new_stem = path.stem + "_comma"
        extension = '.csv'
        return new_stem + extension

    return send_file(io.BytesIO(output_file.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True, download_name=get_output_filename(uploaded_file.filename)
    )


def infer_input(input_mode, input_file):
    if input_mode == 'auto':

        header_candidate = input_file.readline()
        input_file.seek(0)
        try:
            return {
                'dialect': agate.csv.Sniffer().sniff(header_candidate)
            }, None
        except ValueError:
            return None, Response('❗️Could not infer delimiter', 500)
    elif input_mode == 'semicolon':
        return {
            'delimiter': ';'
        }, None
    elif input_mode == 'tab':
        return {
            'delimiter': '\t'
        }, None
    else:
        return None, Response('⚠️Invalid delimiter provided', 400)


def csvformat(input_file, input_kwargs, output_file):
    reader = agate.csv.reader(input_file, **input_kwargs)
    writer = agate.csv.writer(output_file, delimiter=',')
    writer.writerows(reader)



@app.route("/import_google", methods=['POST'])
def import_google():
    # importing locally, due to local python lacking lzma
    from csvkit.utilities.csvsql import CSVSQL

    if 'file' not in request.files:
        return redirect('/')

    uploaded_file = request.files['file']

    if uploaded_file.filename == '':
        return redirect('/')

    output_file = io.StringIO()

    with io.TextIOWrapper(uploaded_file) as input_file:
        try:
            prev_stdin = sys.stdin
            sys.stdin = input_file

            # stub out signal used by csvkit.cli.CSVKitUtility, which doesn't work on app engine
            prev_signal = sys.modules['signal']
            del sys.modules['signal']
            sys.modules['signal'] = __import__('fake_signal')

            csvsql = CSVSQL(
                args=[
                    '--delimiter', "\t",
                    '--query',
                        'select id as "SKU ID", '
                        '"Title" as "Product Name", '
                        '"Google product category" as "Category Name", '
                        'Brand, '
                        'gtin as GTIN, '
                        'size as Size, '
                        'substr(Price, 0, instr(Price, " ")) as Price, '
                        'substr(Price, instr(Price, " ")+1) as Currency, '
                        '"No" as "To Delete?" '
                        'from stdin',
                    ],
                output_file=output_file)
            csvsql.run()
        except Exception as e:
            print("received exception", e, file=sys.stderr)
            raise
        finally:
            sys.stdin = prev_stdin

            del sys.modules['signal']
            sys.modules['signal'] = prev_signal


    def get_output_filename(input_filename):
        path = PurePath(input_filename)
        new_stem = path.stem + "_ttd"
        extension = '.csv'
        return new_stem + extension


    return send_file(io.BytesIO(output_file.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True, download_name=get_output_filename(uploaded_file.filename)
    )

if __name__ == "__main__":
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host="127.0.0.1", port=8080, debug=True)

