from fastapi import FastAPI

app = FastAPI()

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.get("/hello/{name}")
def hello(name: str):
    return {"message": f"Hello, {name}!"}