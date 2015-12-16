# PythonGenerator

This system generates fake python code that is human-readable
and at first glance, appears to be relatively legitimate
code. In particular, we feel that the code generated closely
mirrors code used in industry, since there are no comments.

We read in a corpus of training Python data, and train CFG rules
using those parsed files. We then induce a PCFG using the
relevant frequences of the CFG rules, and attempt to stochastically
generate our own Python "code" based on the PCFG rules, and 
with the help of the Unparser module (we did not create
the Unparser code).

I've included the training data in the repo since it's very small,
about 15 MB.

To run the code, just run
```
./main.py [NUM_FILES]
```
where NUM_FILES is the number of fake Python files you want to 
generate; it is an optional argument, with the default being 5.

## Fetching the Python files (corpus)
If you don't have the Python training files in data/, you can
easily fetch them by first running
```
python data/fetch_python_ids.py
```
and then
```
python data/fetch_python_files.py
```

We use the searchcode API to fetch data.

## Generating fake Python files
The entry point to generate the Python files is the main.py file.
Obviously, the data/ files must exist before running this.

As stated above, it takes an optional argument, the number of
files to generate.

To run it, you can either call
```
python main.py [NUM_FILES]
```
or
```
./main.py [NUM_FILES]
```
when inside the repo.
