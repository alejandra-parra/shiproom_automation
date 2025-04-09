from setuptools import setup, find_packages

setup(
    name="jira_due_date_analysis",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "jira>=3.5.1",
        "pandas>=2.2.0",
        "matplotlib>=3.8.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.4.2",
        "numpy>=1.26.0",
    ],
    python_requires=">=3.11",
)