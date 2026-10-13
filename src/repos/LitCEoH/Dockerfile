FROM continuumio/miniconda3

ENV CONTAINER_ENABLED=True

WORKDIR /ceoh
COPY . /ceoh

RUN rm -f .env

ENV CONDA_ENV_NAME ceoh
RUN conda create --name $CONDA_ENV_NAME python=3.10 -y

RUN /opt/conda/bin/conda run --name $CONDA_ENV_NAME pip install --no-cache-dir -e .

ENV PATH /opt/conda/envs/$CONDA_ENV_NAME/bin:$PATH
RUN echo "source activate $CONDA_ENV_NAME" >> ~/.bashrc

CMD ["bash", "-c", "/bin/bash /ceoh/run_ceoh.sh"]
