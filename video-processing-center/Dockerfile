FROM public.ecr.aws/lambda/python:3.9

RUN yum install wget -y \
 && yum install tar -y \
 && yum install xz -y \
 && cd /usr/local/bin \
 && mkdir ffmpeg \
 && cd ffmpeg \
 && wget https://www.johnvansickle.com/ffmpeg/old-releases/ffmpeg-4.4.1-arm64-static.tar.xz \
 && tar -xf ffmpeg-4.4.1-arm64-static.tar.xz \
 && cd ffmpeg-4.4.1-arm64-static \
 && mv ffmpeg /usr/bin \
 && mv ffprobe /usr/bin

COPY DTTProcessingCenter.py ${LAMBDA_TASK_ROOT}

CMD [ "DTTProcessingCenter.lambda_handler" ]
