#!/usr/bin/env python2.7

"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver

To run locally:

    python server.py

Go to http://localhost:8111 in your browser.

A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@104.196.18.7/w4111
#
# For example, if you had username biliris and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://biliris:foobar@104.196.18.7/w4111"
#
DATABASEURI = "postgresql://jc4697:jacksonaida@35.196.90.148/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
# engine.execute("""CREATE TABLE IF NOT EXISTS test (
#   id serial,
#   name text
# );""")
# engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")

def processSQLObj(obj):
    collection = []
    for result in obj:
        collection.append(result[0])
    return collection

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
#
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """
  cursor = g.conn.execute('SELECT district FROM ElectionDistrict')
  districts = processSQLObj(cursor)
  cursor.close()

  cursor = g.conn.execute('SELECT name FROM PoliticalParty')
  parties = processSQLObj(cursor)
  cursor.close()

  context = {'districts': districts, 'parties': parties}
  return render_template("index.html", **context)

@app.route('/', methods=['POST'])
def create():
    party = request.form['party']
    name = request.form['name']
    address = request.form['address']
    age = request.form['age']
    district = request.form['district']

    try:
        newVoterID = g.conn.execute('SELECT MAX(vid) FROM Voter').fetchone()[0] + 1
        partyID = g.conn.execute("SELECT pid FROM PoliticalParty WHERE name = '{0}'".format(party)).fetchone()[0]
        ballotQuery = """
            SELECT d.bid
            FROM ((ElectionDistrict e JOIN AssociatedWith a ON e.eid = a.eid) JOIN VotingBooth vb ON vb.vbid = a.vbid) JOIN Distribute d ON d.vbid = vb.vbid
            WHERE e.district = '{district}'
            LIMIT 1
        """
        cursor = g.conn.execute(ballotQuery.format(district = district))
        ballot = processSQLObj(cursor)[0]
        cursor.close()

        g.conn.execute("""INSERT INTO Voter (vid, name, address, age)
                          VALUES ({vidinput}, '{nameinput}', '{addressinput}', {ageinput})
                       """.format(vidinput = newVoterID, nameinput = name, addressinput = address, ageinput = age))

        g.conn.execute("""INSERT INTO VoterRegistration (vid, pid)
                          VALUES ({vidinput}, {pidinput})
                       """.format(vidinput = newVoterID, pidinput = partyID))

        g.conn.execute("""INSERT INTO CastBallot (vid, bid)
                          VALUES ({vidinput}, {bidinput})
                       """.format(vidinput = newVoterID, bidinput = ballot))

        return redirect('/')
    except Exception, e:
        return render_template("error.html", error=e)

@app.route('/booth')
def booth():
    try:
      cursor = g.conn.execute("SELECT district FROM ElectionDistrict")
    except Exception, e:
        return render_template("error.html", error=e)
    districts = processSQLObj(cursor)
    cursor.close()

    context = {'ask': True, 'data': districts}
    return render_template("booth.html", **context)

@app.route('/booth', methods=['POST'])
def boothpost():
    try:
        district = request.form['district']

        addressQuery = """
            SELECT v.address, v.waittime
            FROM (ElectionDistrict e JOIN AssociatedWith a ON e.eid = a.eid) JOIN VotingBooth v ON v.vbid = a.vbid
            WHERE e.district = '{district}'
        """
        cursor = g.conn.execute(addressQuery.format(district = district))
        booth = {}
        for result in cursor:
            booth['address'] = result[0]
            booth['wait'] = result[1]
        cursor.close()

        context = {'ask': False, 'booth': booth}
        return render_template("booth.html", **context)
    except Exception, e:
        return render_template("error.html", error=e)


@app.route('/ballot')
def ballot():
    try:
      cursor = g.conn.execute("SELECT name FROM voter")
    except Exception, e:
        return render_template("error.html", error=e)
    names = processSQLObj(cursor)
    cursor.close()

    context = {'ask': True, 'data': names}
    return render_template("ballot.html", **context)

@app.route('/ballot', methods=['POST'])
def ballotpost():
    try:
        name = request.form['name']

        addressQuery = """
            SELECT vb.address, vb.waittime
            FROM (((Voter v JOIN CastBallot c ON v.vid = c.vid) JOIN Ballot B ON c.bid = b.bid) JOIN Distribute d ON d.bid = b.bid) JOIN VotingBooth vb ON vb.vbid = d.vbid
            WHERE v.name = '{voterName}'
        """
        cursor = g.conn.execute(addressQuery.format(voterName = name))
        booth = {}
        for result in cursor:
            booth['address'] = result[0]
            booth['wait'] = result[1]
        cursor.close()

        candidateQuery = """
            SELECT ca.name, ca.platform, (SELECT p.name FROM (Candidate ca2 JOIN AffiliatedWith aw ON ca2.cid = aw.cid) JOIN PoliticalParty p ON p.pid = aw.pid WHERE ca2.cid = ca.cid)
            FROM (((Voter v JOIN CastBallot c ON v.vid = c.vid) JOIN Ballot B ON c.bid = b.bid) JOIN OfferCandidate o ON o.bid = b.bid) JOIN Candidate ca ON ca.cid = o.cid
            WHERE v.name = '{voterName}'
        """
        cursor = g.conn.execute(candidateQuery.format(voterName = name))
        candidates = []
        for result in cursor:
            candidate = {}
            candidate['name'] = result[0]
            candidate['platform'] = result[1]
            candidate['party'] = result[2]
            candidates.append(candidate)
        cursor.close()

        initiativeQuery = """
            SELECT bi.name, bi.title, bi.description
            FROM (((Voter v JOIN CastBallot c ON v.vid = c.vid) JOIN Ballot B ON c.bid = b.bid) JOIN OfferInitiative o ON o.bid = b.bid) JOIN BallotInitiative bi ON bi.biid = o.biid
            WHERE v.name = '{voterName}'
        """
        cursor = g.conn.execute(initiativeQuery.format(voterName = name))
        initiatives = []
        for result in cursor:
            initiative = {}
            initiative['name'] = result[0]
            initiative['title'] = result[1]
            initiative['description'] = result[2]
            print initiative
            initiatives.append(initiative)
        cursor.close()

        context = {'ask': False, 'name': name, 'booth': booth, 'candidates': candidates, 'initiatives': initiatives}
        return render_template("ballot.html", **context)
    except Exception, e:
        return render_template("error.html", error=e)


@app.route('/candidate')
def candidate():
    try:
      cursor = g.conn.execute("SELECT district FROM ElectionDistrict")
    except Exception, e:
        return render_template("error.html", error=e)
    districts = processSQLObj(cursor)
    cursor.close()

    context = {'ask': True, 'data': districts}
    return render_template("candidate.html", **context)

@app.route('/candidate', methods=['POST'])
def candidatepost():
    try:
        district = request.form['district']

        candidateQuery = """
            SELECT c.name, c.platform, (SELECT p.name FROM (Candidate ca2 JOIN AffiliatedWith aw ON ca2.cid = aw.cid) JOIN PoliticalParty p ON p.pid = aw.pid WHERE ca2.cid = c.cid)
            FROM (ElectionDistrict e JOIN RunningIn r ON e.eid = r.eid) JOIN Candidate c ON r.cid = c.cid
            WHERE e.district = '{district}'
        """
        cursor = g.conn.execute(candidateQuery.format(district = district))
        candidates = []
        for result in cursor:
            candidate = {}
            candidate['name'] = result[0]
            candidate['platform'] = result[1]
            candidate['party'] = result[2]
            candidates.append(candidate)
        cursor.close()


        context = {'ask': False, 'candidates': candidates}
        return render_template("candidate.html", **context)
    except Exception, e:
        return render_template("error.html", error=e)

@app.route('/initiative')
def initiative():
    try:
      cursor = g.conn.execute("SELECT district FROM ElectionDistrict")
    except Exception, e:
        return render_template("error.html", error=e)
    districts = processSQLObj(cursor)
    cursor.close()

    context = {'ask': True, 'data': districts}
    return render_template("initiative.html", **context)

@app.route('/initiative', methods=['POST'])
def initiativepost():
    try:
        district = request.form['district']

        initiativeQuery = """
            SELECT bi.name, bi.title, bi.description
            FROM (ElectionDistrict e JOIN OfferedIn o ON e.eid = o.eid) JOIN BallotInitiative bi ON bi.biid = o.biid
            WHERE e.district = '{district}'
        """
        cursor = g.conn.execute(initiativeQuery.format(district = district))
        initiatives = []
        for result in cursor:
            initiative = {}
            initiative['name'] = result[0]
            initiative['title'] = result[1]
            initiative['description'] = result[2]
            initiatives.append(initiative)
        cursor.close()

        context = {'ask': False, 'initiatives': initiatives}
        return render_template("initiative.html", **context)
    except Exception, e:
        return render_template("error.html", error=e)

# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  g.conn.execute('INSERT INTO test VALUES (NULL, ?)', name)
  return redirect('/')

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python server.py

    Show the help text using:

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()
