# PyWebIO Dashboard
View dashboard on https://wang0618.github.io/pywebio-dashboard/

This repo uses [this](https://github.com/wang0618/pywebio-dashboard/actions/workflows/update.yml) github actions to update data periodically, and publish updated data via github page in `web` branch.

### Data update in local environment

1. Follow [this](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token
) to creating a personal access token of Github (only need `repo` permissions) 
   
2. Install dependencies and run data update script:
```bash
pip install -r requirements.txt

GH_USER=<your github username> GH_TOKEN=<your github access token> python update.py
```