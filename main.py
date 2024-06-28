from fastapi import FastAPI # type: ignore

app = FastAPI()

@app.get("/")
async def root():
    return {"greeting": "Hello, World!!!", "message": "Welcome to FastAPI!"}