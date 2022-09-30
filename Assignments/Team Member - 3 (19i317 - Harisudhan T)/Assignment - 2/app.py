import flask
from flask import request, jsonify
app = flask.Flask(__name__)
app.config["DEBUG"] = True

studentData =  [
        {
           "id" : "17",
           "name" : "Harisudhan T",
           "Dept" : "IT",
           "College" : "PSG College of Technology"
        },
        {
           "id" : "23",
           "name" : "Jeevanantham V K",
           "Dept" : "IT",
           "College" : "PSG College of Technology"
        },
        {
           "id" : "24",
           "name" : "Jhanani J",
           "Dept" : "IT",
           "College" : "PSG College of Technology"
        },
        {
           "id" : "26",
           "name" : "Kavi Varshini S",
           "Dept" : "IT",
           "College" : "PSG College of Technology"
        },

    ]

@app.route("/")
def home():
    return "Connection Established !!!!" + "\n" + " Welcome "

@app.route('/user', methods=['GET'])
def get_users():
    return jsonify(studentData)
def get_user_by_id():
    if 'id' in request.args:
        id = int(request.args['id'])
    else:
        return "Error,No id field provided"
    for user in studentData:
        if user['id'] == id:
            return jsonify(user)
    return {}

@app.route("/user/<id>", methods=['GET'])
def get_user_by_id_in_path(id):
    for user in studentData:
        if user['id'] == int(id):
            return jsonify (user)
    return {}

@app.route('/add_user', methods=['POST'])
def post_users():
    user = request.get_json()
    user['id'] = len(users_dict) + 1
    users_dict.append(user)
    return jsonify(user)

@app.route('/update_user', methods=['PUT'])
def put_users():
    user = request.get_json()
    for i, u in enumerate(studentData):
        if u['id'] == user['id']:
            users_dict[i] = user
    return {}


@app.route('/delete/', methods=['DELETE'])
def delete_users(id):
    for user in studentData:
        if user['id'] == int(id):
            studentData.remove(user)
    return {}

if __name__=="__main__":
    app.run()
