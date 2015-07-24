# Version 0.2.0 #

## Supported Features ##

  * Sending and receiving messages
  * Setting and receiving presence and moods
  * Editing and removing contacts
  * Adding new contacts
  * Automatically accepts invitations from contacts
  * Basic support for MultiMX rooms

## Commands ##

Not all MXit features can be directly implemented using the Empathy interface. For these features, we created text commands, that can be used in any chat window. These commands are for:
  * Creating a MultiMX room: /create
  * Inviting someone to a MultiMX room: /invite
  * Setting your mood: /mood

For more information on these commands, use /help command

## Known Issues ##
  * Encoding is not done proberly yet - might crash if you use non-ASCII characters. (fixed in 0.2.1)
  * If you are idle for about 40 minutes, the server will stop sending messages, without notifying the client. This seems to be a server-side issue, and also happens with the official client.


## Features not supported yet ##
  * File transfers
  * Encrypted messages
  * Formatted messages
  * Clickable service messages

## Dependancies ##
`python-telepathy` is required to be able to run `telepathy-mixer`.

The release includes a compatible version of pymxit.

## Compatibility ##
This release is based on version 0.17.x of the [Telepathy Specification](http://telepathy.freedesktop.org/spec.html). This means that recent versions of Empathy and Telepathy, which support this specification, are required.

Known to work with Empathy 0.22.1 and python-telepathy 0.14.0 and later. These are included in the Ubuntu Hardy and Intrepid universe repositories.

# Version 0.2.1 #
  * Character encoding is handled properly now. If try to send any invalid characters, it will be replaced with question marks.