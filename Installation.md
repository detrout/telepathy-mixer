Current version: 0.2.1

# Installation on Ubuntu 8.04 and 8.10 #

In Synaptic Package Manager make sure you have the universe repository enabled, and install "empathy" and "python-telepathy".

From the downloads page, download telepathy-mixer-0.2.1.tar.gz and extract it anywhere.

In a terminal, go the the directory where it was extracted, for example:
```
cd /home/user/telepathy-mixer-0.2.1/
```

The run:

```
./configure
make
sudo make install
```

Now when you run Empathy, you should be able to add an account of type MXit.


# Other Linux Distributions #
See the following pages for installing the different components. Once you have Empathy running, all you need is telepathy-python - then follow the instructions as for Ubuntu.

  * http://mission-control.sourceforge.net/
  * http://live.gnome.org/Empathy/Install
  * http://telepathy.freedesktop.org/wiki/Telepathy%20Python

# Creating an account #

Go to http://www.mxit.co.za/wap/ and download the mobile client (jad file only).

Tested to work with these options:
  * English
  * New user
  * Choose phone -> Nokia -> 2630
  * Accept version 5.3.0
  * South Africa
  * Normal version

This will give you a jad file. Open it with any text editor. Copy the code on the line starting with "c: ". It be in this form:

XXXXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXXXXXXXXXX

Now run Empathy, and go to the account manager. Create a new account of type MXit. In the Client\_id field, paste the code you just copied. Account is your phone number, in the format 27821234567. Password is your MXit pin.

Note that the codes cannot be reused for different accounts.

# Troubleshooting #
If MXit is not listed under the account types in Empathy, something went wrong with the installation.

If you can create an account, but cannot connect, the most probably cause is not installing python-telepathy. If you still cannot connect, run the following in a terminal, _just before connecting_:
```
/usr/local/libexec/telepathy-mixer
```

Send the output of this to the mailing list.
Note that the script stops within a few seconds if you are not connected.

# Feedback #

This is still in development, and will probably contain many bugs. Please let me know what your experience is. Please ask any questions on the [mailing list](http://groups.google.com/group/telepathy-mixer).