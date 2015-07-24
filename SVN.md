telepathy-mixer depends on pymxit and python-telepathy.

If you are running Ubuntu, python-telepathy can be installed from the package manager.

pymxit can be checked out with:
> `svn checkout http://pymxit.googlecode.com/svn/trunk/src/ pymxit-read-only`


and telepathy-mixer:
> `svn checkout http://telepathy-mixer.googlecode.com/svn/trunk/ telepathy-mixer-read-only`


Install telepathy-mixer as explained in [Installation](Installation.md), and make sure that the mxit folder from pymxit is in the python path - `/usr/local/lib/python2.5/site-packages/` should work.

# Debugging #
To see debugging output, run telepathy-mixer directly from a terminal, before going online in Empathy.