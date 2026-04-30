from fastapi import FastAPI
from .app.routes import router

app = FastAPI(title="CloudVisor CIEM Service")

app.include_router(router)

def run():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)

if __name__ == "__main__":
    run()