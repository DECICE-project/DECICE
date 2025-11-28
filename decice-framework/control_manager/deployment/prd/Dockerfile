FROM https://gitlab-ce.gwdg.de/decice/decice-wp3:control-manager-base

# Everthing which you need for prd like exporter ... #

WORKDIR /app
COPY . /app


EXPOSE 8000

CMD ["python","./src/main.py"]