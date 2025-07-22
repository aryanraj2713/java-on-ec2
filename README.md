


<img width="8105" height="11074" alt="Untitled-2025-07-22-1818-2" src="https://github.com/user-attachments/assets/95c49cb9-ffab-47d6-9aef-273874d290d6" />


## Setup

1. **Deploy infrastructure**
   ```bash
   ./scripts/setup-infrastructure.sh dev eu-north-1
   ```

2. **Add GitHub secrets**
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

3. **Configure AWS Secrets Manager**
   ```bash
   # SSH key for repo access
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/deployment_key
   aws secretsmanager create-secret --name java-app-ssh-key-dev --secret-string "$(cat ~/.ssh/deployment_key)"
   
   # Logfire token
   aws secretsmanager create-secret --name LF_TOKEN --secret-string "your-logfire-token"
   ```

4. **Add deploy key to GitHub**
   - Copy `~/.ssh/deployment_key.pub`
   - Add to GitHub repo: Settings > Deploy keys

## How it works

- Push to `main`/`develop` triggers deployment
- Spins up EC2 t3.micro instance (AWS Free Tier)
- Clones repo, builds JAR, starts Java app
- Runs for ~10 minutes, then auto-terminates
- Full Logfire logging and monitoring

## Cost

~$0.00/month (only AWS Secrets Manager after free trial)

## Local testing

```bash
python3 deployment_script.py git@github.com:your-org/repo.git --port 9000
``` 
