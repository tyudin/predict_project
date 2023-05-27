FROM python:3.10-slim
RUN mkdir -p /app/model
RUN mkdir -p /app/static
RUN mkdir -p /app/templates
WORKDIR /app
COPY ./requirements.txt /app
COPY ./run_server.py /app
COPY ./model/model.dill /app/model
COPY ./static/styles.css /app/static
COPY ./templates/predict.html /app/templates
# RUN pip3 install --upgrade pip -r requirements.txt
RUN pip3 install -r requirements.txt
EXPOSE 5000
ENTRYPOINT ["gunicorn", "-w 2", "-b 0.0.0.0:5000", "run_server:app"]