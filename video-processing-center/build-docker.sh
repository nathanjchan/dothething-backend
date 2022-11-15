aws ecr get-login-password --region us-west-1 | docker login --username AWS --password-stdin 862592418544.dkr.ecr.us-west-1.amazonaws.com
docker build -t dothething-video-processing-center .
docker tag dothething-video-processing-center:latest 862592418544.dkr.ecr.us-west-1.amazonaws.com/dothething-video-processing-center:latest
docker push 862592418544.dkr.ecr.us-west-1.amazonaws.com/dothething-video-processing-center:latest
