
from flask import Blueprint,render_template,Flask,current_app,jsonify,request
from flask_login import login_user,logout_user,LoginManager,login_required
from flask import render_template
from flask_socketio import SocketIO,emit
from extensions import socketio
import json

from .sql import*


pschyo=Blueprint('pschyo',__name__)

@login_required
@pschyo.route("/chats")
def chats():
    return render_template("community.html")

@login_required
@pschyo.route('/some_endpoint',methods=['GET'])
def handle_message():

    data=request.get_json()
    current_app.logger.info("Received message:"+data['message'])

@login_required
@socketio.on("send_message")
def handle_send_message_event(data):
    current_app.logger.info("Received message: "+data['message'])
    emit('receive_message',data,broadcast=True)

@login_required
@socketio.on("send_image")
def handle_send_image_event(data):
    current_app.logger.info("Received image from: "+data['username'])
    emit('receive_image',data,broadcast=True)
