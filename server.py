from fastapi import FastAPI
import zmq
import time

context = zmq.Context()
ip = "tcp://0.0.0.0:8500"
zmq_socket = context.socket(zmq.REQ)
zmq_socket.connect(ip)
time.sleep(2)
##################################################### Server Endpoints ##########################################################

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Endpoint for WikiSummarizer SlackBot"}

@app.post("/")
async def root(reqbody: dict):
    print("\n", reqbody)
    if "challenge" in reqbody:
        return {"challenge": reqbody["challenge"]}
    else:
        if "event" in reqbody:
            # handleEvent(reqbody["event"])
            zmq_socket.send_json(reqbody["event"])
            return zmq_socket.recv_json()
        return {}