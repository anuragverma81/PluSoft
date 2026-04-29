
from flask import Blueprint,render_template,request,flash,redirect,url_for,current_app
from flask_login import login_required

from flask import Flask,session
from flask import render_template
from flask import request
from flask import redirect,url_for
from flask_socketio import SocketIO,emit
from extensions import socketio
from flask_socketio import join_room
from flask_socketio import leave_room
from flask_socketio import send
import string
import random
from string import ascii_uppercase

from functools import wraps
import sqlite3

from .sql import*



server=Blueprint('server',__name__)


rooms={}
def generate_unique_code(length):
    while True:
        code=""
        for _ in range(length):
            code+=random.choice(ascii_uppercase)

        if code not in rooms:
            break
    return code


@login_required
@server.route('/channel')
def channel():
    return render_template("channel.html")

@login_required
@server.route('/create',methods=['POST','GET'])

def create():

    if request.method=='POST':
        name = request.form.get("name")
        code = request.form.get("code")
        join=request.form.get("join")
        create = request.form.get("create", False)

        if not name:
            return render_template("create.html", error="Please enter the username", code="code", name="name")

        if join and not code:
            return render_template("create.html", error="Please enter the room code", code="code", name="name")

        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("create.html", error="Room does not exist!!", code="code", name="name")

        session["room"] = room
        session["name"] = name
        return redirect(url_for("server.room"))


    return render_template("create.html")




@login_required
@server.route('/join',methods=['POST','GET'])
def join():

    if request.method=='POST':

        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join")
        create = request.form.get("create", False)

        if not name:
            return render_template("join.html", error="Please enter the username", code="code", name="name")

        if join and not code:
            return render_template("join.html", error="Please enter the room code", code="code", name="name")

        room = code
        if create != False:
            room = generate_unique_code(4)

            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("join.html", error="Room does not exist!!", code="code", name="name")

        session["room"] = room
        session["name"] = name
        return redirect(url_for("server.room"))



    return render_template("join.html")



@login_required
@server.route("/room")

def room():
    room=session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("server.channel"))
    return render_template("room.html",code=room,messages=rooms[room]["messages"])

@socketio.on("connect")
def connect():
    room=session.get("room")
    name=session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    join_room(room)
    send({"name": name, "message":" has entered"},to=room)
    rooms[room]["members"] +=1
    print(f" {name} joined room {room} ")



@socketio.on("message")
def message(data):
    room=session.get("room")
    name=session.get("name")

    if not room or not name:
        print("Error:Room or name is missing ")
        return
    if room not in rooms:
        print(f"Error:Room'{room}' does not exist")
        return
    print(f"{session.get('name')} said:{ data['data']}")

    content={
        "name": session.get("name"),
        "message" : data["data"]

    }
    send(content,to=room)
    rooms[room]["messages"].append(content)





@socketio.on("disconnect")
def disconnect():
    room=session.get("room")
    name=session.get("name")
    leave_room(room)
    if room in rooms:
        rooms[room]["members"] -=1
        if rooms[room]["members"]<=0:
            del rooms[room]
    send({"name":name,"message":" has leave the room" },to=room)
    print(f"{name} leaved the room{room}")


@socketio.on("send_image")
def handle_send_image_event(data):
    current_app.logger.info("Received image from: "+data['username'])
    emit('receive_image',data,broadcast=True)
