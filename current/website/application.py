import requests
from pydantic import BaseModel
from flask import render_template_string,Blueprint
from flask import Blueprint,render_template,request,flash,redirect,url_for,current_app
from flask_login import login_required

from .sql import*

application=Blueprint('application',__name__)



class ResearchResponse(BaseModel):
    topic:str


template = (
    "You are a financial AI assistant specialized in extracting precise, relevant financial data from user queries. "
    "Please adhere to the following rules strictly:\n\n"
    "1. **Extract Only Relevant Financial Information**: Respond only with data that directly matches the financial topic or metric requested.\n"
    "2. **No Extra Commentary**: Do not include any explanations, opinions, or additional context.\n"
    "3. **Empty Response for No Match**: If no relevant financial data is found, respond with: 'Sorry for the inconvenience.'\n"
    "4. **Data-Only Output**: Your response should contain only the requested financial figures, terms, or statements — no preamble or closing remarks."
)




api_key='xE00gPGTUgup4e6Mz3hNEPRmkbpwwpFN'
url='https://api.mistral.ai/v1/chat/completions'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}




@login_required
@application.route("/agent",methods=['POST','GET'])



def index():
    if request.method=='POST':
        query=request.form.get("query")

        if not query:
            return "Missing Query."

        prompt=f"{template}\n\nExtract information about:{query}"

        data = {
            'model': 'open-mixtral-8x22b',
             'messages':[{
                 'role':'user','content':prompt
             }]}
        try:
            response=requests.post(url,headers=headers,json=data)
            if response.status_code==200:
                result=response.json()['choices'][0]['message']['content']

            else:
                result=f"API ERROR:{response.status_code} - {response.text}"

        except Exception as e:
            result=f"Request failed:{e}"
        return render_template("research.html",result=result,response=response)

    return render_template("agent.html")


