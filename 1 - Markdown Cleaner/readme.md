

### Install
```
pip install pyinstaller

```
### Compile to .exe
```
pyinstaller --onefile --name md-cleaner main.py

```


```
md-cleaner.exe
md-cleaner.exe --verbose
md-cleaner.exe -i custom.md -o my_output
```

```bash

python main.py


python main.py --input path/to/myfile.md

python main.py --verbose

python main.py -i myfile.md -o results -v
```