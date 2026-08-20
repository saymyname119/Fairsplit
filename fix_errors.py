import re
import glob

files = glob.glob('modules/**/*.py', recursive=True)
for f in files:
    with open(f, 'r') as file:
        content = file.read()
    
    new_content = re.sub(r'(DomainError|ConflictError|ForbiddenError)\("[^"]*",\s*(f?"[^"]*")\)', r'\1(\2)', content)
    
    if new_content != content:
        with open(f, 'w') as file:
            file.write(new_content)
