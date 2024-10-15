FROM ubuntu:24.04
LABEL com.polyhedralcc.version="1.0"

ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN  apt-get update \
  && apt-get install -y wget make m4 build-essential patch unzip git libgmp3-dev \
  && rm -rf /var/lib/apt/lists/*

RUN apt-get update \ 
  && apt-get install -y gcc g++ g++-multilib gfortran flex bison automake autoconf libtool pkg-config make perl doxygen texinfo texlive-latex-extra wget rsync llvm-14-dev libclang-14-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /pluto/

# Install Pluto
RUN git clone https://github.com/bondhugula/pluto \
  && cd pluto/ \
  && git submodule init \
  && git submodule update \
  && ./autogen.sh \
  && ./configure --with-clang-prefix=/usr/lib/llvm-14
RUN cd pluto && make -j$(nproc)

WORKDIR /pocc/

# Install POCC
RUN wget https://master.dl.sourceforge.net/project/pocc/1.6/release/pocc-1.6.0-alpha-selfcontained.tar.gz?viasf=1 -O pocc-1.6.0-alpha-selfcontained.tar.gz \
  && tar -xvf pocc-1.6.0-alpha-selfcontained.tar.gz \
  && cd pocc-1.6.0-alpha \
  && ./install.sh 

# Export PATH
ENV PATH="$PATH:/pocc/pocc-1.6.0-alpha/bin"
ENV PATH="$PATH:/pluto/pluto"

# Install Python3 and pip
RUN apt-get update \
  && apt-get install -y python3 python3-pip python3.12-venv \
  && rm -rf /var/lib/apt/lists/*

# Install PAPI
RUN apt-get update \
  && apt-get install -y libpapi-dev \
  && rm -rf /var/lib/apt/lists/*

# Install AARCH64 cross compiler
RUN apt-get update \
  && apt-get install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu \
  && rm -rf /var/lib/apt/lists/*

# Install CMake
RUN apt-get update \
  && apt-get install -y cmake \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /gem5/

# Install dependencies for gem5
RUN apt-get update \ 
  && apt install -y build-essential scons python3-dev git pre-commit zlib1g zlib1g-dev \
     libprotobuf-dev protobuf-compiler libprotoc-dev libgoogle-perftools-dev \
     libboost-all-dev  libhdf5-serial-dev python3-pydot python3-venv python3-tk mypy \
     m4 libcapstone-dev libpng-dev libelf-dev pkg-config wget cmake doxygen \ 
  && rm -rf /var/lib/apt/lists/*

# Install gem5
RUN git clone https://github.com/gem5/gem5 \
  && cd gem5 \
  && scons build/X86/gem5.fast -j$(nproc)
  
# Build util/m5
RUN cd gem5/util/m5 \
  && scons build/x86/out/libm5.a

ADD gus /gus

WORKDIR /gus/

# Install dependencies for GUS

RUN apt-get update && \
    env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential gcc g++ clang cmake ninja-build time file \
    libtinfo-dev zlib1g-dev libedit-dev libxml2-dev \
    python3 python3-dev python3-setuptools python3-pip \
    git curl wget openssl ca-certificates gnupg \
    gosu sudo \
    doxygen libglib2.0-dev \
    lsb-release wget software-properties-common gnupg libiberty-dev \
    gcc-aarch64-linux-gnu python3-venv \
 && rm -rf /var/lib/apt/lists/*
 
# Install GUS

RUN mkdir build \
  && cmake -B build -DSIMULATED_ARCH=x86_CLX_UOPS \
  && make -C build -j 1 \
  && make -C build install

# Export PATH
ENV PATH="$PATH:/gus/build/bin"
ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/gus/build/lib"

RUN python3 -m pip install -r requirements.txt --break-system-packages

ENTRYPOINT ["bash"]