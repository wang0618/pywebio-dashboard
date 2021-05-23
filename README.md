# PyWebIO Dashboard

### Update data

1. Follow [this](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token
) to creating a personal access token of Github (only need `repo` permissions) 
   
2. 
```bash
pip install -r requirements.txt

GH_USER=<your github username> GH_TOKEN=<your github access token> python update.py
```