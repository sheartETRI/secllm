## 1. Setup
### 1.1 Virtual Environment
python -m venv venv<br>
source venv/bin/activate

### 1.2 Installation
pip install -r requirements.txt

### 1.3 OPENAI_API_KEY
vi ~/.bashrc
add the following line
- export OPENAI_API_KEY='sk-(YOUR_API_KEY)'<br>
source ~/.bashrc

## 2. download SKKU LLM model
python download_model.py

## 3. extract SKKU Detector model
cd models<br>
sh restore.sh

## 4. Setup CodeQL
### 4.1  **Download CodeQL CLI**:
  Go to [CodeQL CLI GitHub Releases](https://github.com/github/codeql-cli-binaries/releases) and download the CodeQL 2.11.2 for your operating system.
  - [Linux](https://github.com/github/codeql-cli-binaries/releases/download/v2.11.2/codeql-linux64.zip)
  - [Mac](https://github.com/github/codeql-cli-binaries/releases/download/v2.11.2/codeql-osx64.zip)
  - [Windows](https://github.com/github/codeql-cli-binaries/releases/download/v2.11.2/codeql-win64.zip)

### 4.2 **Extract the downloaded file**:
  Extract the compressed archive to a folder on your machine.

### 4.3 **Set up environment variables**:
mkdir ~/codeql-home<br>
mv codeql-linux64.zip ~/codeql-home<br>
cd ~/codeql-home<br>
unzip codeql-linux64.zip<br>
Add the extracted folder to your system’s `PATH` environment variable to make CodeQL accessible from any directory.<br>
vi ~/.bashrc<br>
add the following lines
- CODEQL_HOME=(YOUR_HOME_PATH)/codeql-home/codeql
- export CODEQL_HOME
- PATH=$CODEQL_HOME:$PATH
source ~/.bashrc


### 4.4 **Verify Installation**:
  Run the following command to verify the installation:

  ```bash
  $ codeql --version
  CodeQL command-line toolchain release 2.11.2.
  Copyright (C) 2019-2022 GitHub, Inc.
  Unpacked in: /home/jan087/codeql-home/codeql
    Analysis results depend critically on separately distributed query and
    extractor modules. To list modules that are visible to the toolchain,
    use 'codeql resolve qlpacks' and 'codeql resolve languages'.
  ```

  If installed correctly, this will display the current version of the CodeQL CLI.

### 4.5 **Download CodeQL Packs**:
  Download the CodeQL packs for the languages you want to analyze.

  ```bash
  $ cd ~/codeql-home
  $ git clone --recursive https://github.com/github/codeql.git codeql-repo
  $ cd codeql-repo
  $ git checkout codeql-cli/v2.11.2
  ```

### 4.6. **Resolve qlpacks and language packs**:
  Run the following commands to resolve the qlpacks and language packs:

  ```bash
  $ cd $CODEQL_HOME
  $ ls -al
  ...
  drwxr-xr-x 17 jan087 jan087  310 Oct 24  2022 codeql
  drwxrwxr-x 20 jan087 jan087 4096 Aug 14 08:37 codeql-repo
  $ codeql resolve qlpacks
  $ codeql resolve languages
  ```

### 4.7. **Copy Top25 Queries**:
  Copy the Top25 queries from this repo to `codeql-repo`:

  ```bash
  $ cp -r PATH/TO/secllm/codeql-queries/cpp/top25 ~/codeql-home/codeql-repo/cpp/ql/src/
  $ cp -r PATH/TO/secllm/codeql-queries/python/top25 ~/codeql-home/codeql-repo/python/ql/src/
  ```

## execute uvicorn
uvicorn main:app --reload

## execute demo
python demo.py
