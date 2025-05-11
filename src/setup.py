from setuptools import setup, find_packages

setup(
    name="vehicle_counter",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "ultralytics>=8.0.0",
        "opencv-python>=4.5.0",
        "deep-sort-realtime>=1.3.0",
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "pydantic>=1.8.0",
        "numpy>=1.19.0",
    ],
    python_requires=">=3.8",
    author="Developers",
    author_email="info@example.com",
    description="Тээврийн хэрэгсэл тоолох, түгжрэлийн түвшин тодорхойлох сервис",
    long_description=open("src/vehicle_counter/README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/vehicle_counter",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 