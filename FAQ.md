
---


  * The GUI fail to start on Windows.
    * For **v.0.1.0 and below**:
> > > This is some upstream bug that we have no idea of how to fix. Here is the [workaround](http://code.google.com/p/mainframe-env-simulator/issues/detail?id=1).
    * For **v.0.1.2 and above** (including svn version):
> > > Make sure you do **`python setup.py build`** before **`python setup.py bdist_wininst`**


---


  * The command ```python setup.py build``` failed to retrieve revision number on Windows.

> > That is another upstream Windows-only bug. Delete "setup.cfg" in the source folder and try again.


---


  * I'd like to use SVN version, how do I keep it up-to-date?
> > To make use of SVN version, instead of
```
$ python setup.py build
$ sudo python setup.py install --record install.record.txt
```
> > or
```
> python setup.py build
> python setup.py bdist_wininst
> dist\mainframe-env-simulator-*.exe
```
> > use **```[sudo] python setup.py develop```**, which will install **links** pointing back to the source folder. Now every time you do an ```svn update``` in the source folder, the simulator will automatically updated accordingly, unless the structure of the project changed (in which case, you need to run ```python setup.py develop``` again).


---
