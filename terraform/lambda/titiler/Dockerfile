FROM public.ecr.aws/lambda/python:3.12

WORKDIR /tmp

# Install system dependencies to compile (numexpr)
RUN dnf install -y gcc-c++ && dnf clean all

RUN python -m pip install pip -U
RUN python -m pip install "titiler.application==0.23.1" "mangum>=0.19.0" -t /asset --no-binary pydantic

# Reduce package size and remove useless files
RUN cd /asset && find . -type f -name '*.pyc' | while read f; do n=$(echo $f | sed 's/__pycache__\///' | sed 's/.cpython-[0-9]*//'); cp $f $n; done;
RUN cd /asset && find . -type d -a -name '__pycache__' -print0 | xargs -0 rm -rf
RUN cd /asset && find . -type f -a -name '*.py' -print0 | xargs -0 rm -f
RUN find /asset -type d -a -name 'tests' -print0 | xargs -0 rm -rf
RUN rm -rdf /asset/numpy/doc/ /asset/boto3* /asset/botocore* /asset/bin /asset/geos_license /asset/Misc

# Ref: https://github.com/developmentseed/titiler/discussions/1108#discussioncomment-13045681
RUN cp /usr/lib64/libexpat.so.1 /asset/

# Add your app
COPY handler.py /asset/handler.py

WORKDIR /asset
RUN python -c "from handler import handler; print('All Good')"

# Create the deployment package
RUN zip -r /tmp/lambda-package.zip .

# Default command - can be overridden
CMD ["echo", "Lambda package built successfully"]
