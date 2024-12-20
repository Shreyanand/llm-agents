from dotenv import load_dotenv
load_dotenv()
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
import mlflow
from react_agent.agent import react_agent
from react_agent.apispec import ReActRequest, ReActResponse
from react_agent.constants import APP_HOST, APP_PORT, MLFLOW_EXPERIMENT_NAME, MLFLOW_TRACKING_URI, MLFLOW_TRACKING_TOKEN
logger = logging.getLogger(__name__)

# Connect to a hosted mlflow
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
if not mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME):
    mlflow.create_experiment(name=MLFLOW_EXPERIMENT_NAME)

experiment = mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME)
experiment_id = experiment.experiment_id

# Start logging
with mlflow.start_run(experiment_id=experiment_id):
    mlflow.langchain.autolog(log_traces=True)

agents = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup sequence."""
    # Add them to the application components
    agents["react"] = react_agent()

    logger.info("Startup sequence successful")
    yield
    agents.clear()


app = FastAPI(lifespan=lifespan)


@app.post("/react", response_model=ReActResponse)
async def react(request: ReActRequest):
    """Interact with the ReAct agent."""
    agent = agents["react"]

    # Send it to the agent
    agent_response = agent.invoke({"input": request.prompt, "chat_history": []})
    answer = agent_response["output"]
    response = ReActResponse(answer=answer)
    return response

@app.route("/health")
def health():
    """Perform a service health check."""
    return {"status": "ok"}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    uvicorn.run(app, port=APP_PORT, host=APP_HOST)