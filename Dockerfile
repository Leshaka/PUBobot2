FROM python:3.9.6-slim-buster

# required to install packages
USER 0

# hadolint ignore=DL3008
RUN DEBIAN_FRONTEND=non-interactive apt-get update && \
    DEBIAN_FRONTEND=non-interactive apt-get install --no-install-recommends -y \
      ca-certificates \
      gettext \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/

# add user to run app
RUN mkdir -p /home/bot \
    && echo "bot:x:1001:65534:Linux User,,,:/home/bot:/sbin/nologin" >> /etc/passwd \
    && chown 1001 /home/bot

WORKDIR /home/bot
COPY . .
RUN chown -R 1001:1001 /home/bot

# set default user to run app as non-root
USER 1001
ENV PATH="/home/bot/.local/bin:$PATH"
RUN pip3 --no-cache-dir install -r requirements.txt

RUN ./compile_locales.sh

# PYTHONDONTWRITEBYTECODE: Do not write byte files to disk, since we maintain it as readonly. (equivalent to `python -B`)
ENV PYTHONDONTWRITEBYTECODE=1
# PYTHONHASHSEED: Enable hash randomization (equivalent to `python -R`)
ENV PYTHONHASHSEED=random
# PYTHONUNBUFFERED: Force stdin, stdout and stderr to be totally unbuffered. (equivalent to `python -u`)
ENV PYTHONUNBUFFERED=1


# EXPOSE 5000

CMD ["python3", "PUBobot2.py"]
