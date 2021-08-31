import sqlite3
import logging
import sys
import os

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort

connection_count = 0

def get_db_connection():
  #Global variable to hold number of times a db connection has been made.
    global connection_count
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    connection_count += 1

    return connection

# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    return post

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

# Define the main route of the web application 
@app.route('/')
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    if post is None:
        app.logger.error('Article with id: "{}" not found!'.format(post_id))
        return render_template('404.html'), 404
    else:
        app.logger.info('Article "{}" retrieved!'.format(post["title"]))
        return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.info('About Us page has been retrieved.')
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()

            app.logger.info('Article: "{}" has been created.'.format(title))
            return redirect(url_for('index'))

    return render_template('create.html')

# Define the healthz endpoint
@app.route('/healthz', methods=['GET'])
def healthz():
    app.logger.info('Status request successful!')
    try:
        connection = get_db_connection()
        count = connection.execute('select count(1) from posts').fetchone()
        return jsonify(result='OK - healthy'), 200
    except sqlite3.DatabaseError as err:
        return jsonify(result='ERROR - unhealthy: {}'.format(err)), 500

# Define the metrics endpoint
@app.route('/metrics', methods=['GET'])
def metrics():
    app.logger.info('Metric endpoint is reached!')
    connection = get_db_connection()
    count = connection.execute('select count(1) from posts').fetchone()
    connection.commit()
    connection.close()
    return jsonify(post_count=count[0], db_connection_count=connection_count), 200

# start the application on port 3111
if __name__ == "__main__":
    # Set up logging
    logger = logging.getLogger('techtrends_app_logger')
    # Set loglevel to an Environment Variable
    loglevel = os.getenv("TECHTRENDS_APP_LOGLEVEL", "DEBUG").upper()
    # Set logging output type dynamically depending on loglevel condition
    loglevel = (
        getattr(logging, loglevel)
        if loglevel in ["CRITICAL", "DEBUG", "ERROR", "INFO", "WARNING"]
        else logging.DEBUG
        ) 
    # Set logger to handle STDOUT and STDERR
    stdout_handler = logging.StreamHandler(sys.stdout)
    stderr_handler = logging.StreamHandler(sys.stderr)

    # Set the lowest threshold that gets logged to stderr
    stdout_handler.setLevel(logging.DEBUG)
    stderr_handler.setLevel(logging.ERROR)

    # Add handlers to our logger
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
    handlers = [stdout_handler, stderr_handler]

    logging.basicConfig(level = logging.DEBUG,
        format = '%(levelname)s:%(name)s - - %(asctime)s: %(message)s',
        handlers=handlers)
    app.run(host='0.0.0.0', port='3111')