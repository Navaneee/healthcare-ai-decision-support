from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
from custom_tool import GuidelineRAGTool

# ─── Initialize Ollama LLM ───────────────────────────────────────
llm = LLM(
    model="ollama/mistral",
    base_url="http://localhost:11434",
    timeout=1800,
    temperature=0.1,
    max_tokens=1024
)

# ─── Initialize RAG Tool ─────────────────────────────────────────
guideline_rag_tool = GuidelineRAGTool()

@CrewBase
class MedicalAnalysisCrew():
    """Medical Report Analysis Crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    # ─── Agents ──────────────────────────────────────────────────

    @agent
    def report_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['report_analyzer'],
            llm=llm
        )

    @agent
    def guideline_retriever(self) -> Agent:
        return Agent(
            config=self.agents_config['guideline_retriever'],
            llm=llm,
            tools=[guideline_rag_tool]
        )

    @agent
    def risk_explainer(self) -> Agent:
        return Agent(
            config=self.agents_config['risk_explainer'],
            llm=llm
        )

    @agent
    def safety_validator(self) -> Agent:
        return Agent(
            config=self.agents_config['safety_validator'],
            llm=llm
        )

    # ─── Tasks ───────────────────────────────────────────────────

    @task
    def medical_report_extraction_task(self) -> Task:
        return Task(
            config=self.tasks_config['medical_report_extraction_task'],
        )

    @task
    def guideline_retrieval_task(self) -> Task:
        return Task(
            config=self.tasks_config['guideline_retrieval_task'],
        )

    @task
    def risk_assessment_task(self) -> Task:
        return Task(
            config=self.tasks_config['risk_assessment_task'],
        )

    @task
    def safety_validation_task(self) -> Task:
        return Task(
            config=self.tasks_config['safety_validation_task'],
        )

    # ─── Crew ────────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )