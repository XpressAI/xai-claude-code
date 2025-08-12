from setuptools import setup, find_packages

setup(
    name="xai-claude-code",
    version="0.1.0",
    description="Xircuits components for Claude Code CLI integration",
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    author="XpressAI",
    author_email="hello@xpress.ai",
    url="https://github.com/xpressai/xai-claude-code",
    packages=find_packages(),
    py_modules=["claude_code_components"],
    install_requires=[
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="xircuits, claude, ai, cli, automation, components",
    project_urls={
        "Documentation": "https://github.com/xpressai/xai-claude-code#readme",
        "Source": "https://github.com/xpressai/xai-claude-code",
        "Tracker": "https://github.com/xpressai/xai-claude-code/issues",
    },
)
