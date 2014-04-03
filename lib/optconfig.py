#!/usr/bin/env python
# /* Copyright 2013 Proofpoint, Inc. All rights reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#	 http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# */

myhelp = '''
=head1 NAME

Optconfig - Configure and parse command-line options

=head1 SYNOPSIS

# Invoking an optconfig program

program [options] arguments...
   --config=file	Use file for configuration
   --verbose		Produce verbose output
   --dry-run		Do a dry run (don't change things)
   --version		Print program version number
   --help		   Print usage message
   --debug		  Produce debugging output
   Some programs will have options specific to them

# In optconfig program
import optconfig,sys,os

# Configuration is read from
opt = optconfig.new('domain', { 'force!': 0, 
								'logfile=s': '/var/log/foo',
								'define=s%': {
									'mail' : 'bob@myhost.com'
								}
							  })
if opt{'force!'}:
	os.unlink(filefoo)

fh = open(opt{'logfile'}, "w")
fh.write("Message\n")

for k in opt{'define'}:
   print "$key = $opt->{'define'}->{$key}\n";
}

=head1 DESCRIPTION

The Optconfig module looks in various places for its configuration. It will
read configuration from I<one> of C<$HOME/.domain>,
C</opt/pptools/etc/domain.conf> and the configuration file (if any) specified
with the B<--config> command-line option.

The whole configuration is read from the file (even if the option spec doesn't
contain those configuration items), and values can be overridden by
command-line options specified in the option spec.

There is a standard set of options you can pass (or configure in a config
file) to Optconfig programs.

=head2 Standard Options

=over

=item --config=file

Optconfig reads the configuration in the named file. The configuration file
format is JSON.  If it can't read this file, it complains. If no --config
option is specified, it will search for a configuration file in the standard
locations as listed above. If it finds a file, it reads it and sets config
values accordingly, then overrides or merges these values with the ones on
the command line.

Some options can be specified multiple times. For example, a --define option
might allow you to define more than one key; or a --host option might allow
you to define more than one host. If these options appear in the configuration
file and the command line, their values are added to by the command line value
For example, if you have a configuration file with the following contents:

{ "define": { "name": "bob", "home": "/home/bob" }
  "host": [ "wiki.ppops.net", "tickets.ppops.net" ] }

And you pass C<--define mail=bob@proofpoint.com> C<--host=mail.ppops.net> into
the command, the resulting configuration will be:

{ "define": { "mail": "bob@proofpoint.com", "name": "bob",
			  "home": "/home/bob" },
  "host": [ "mail.ppops.net", "wiki.ppops.net", "tickets.ppops.net" ] }

Note how the command-line value for C<--host> is prepended to the list.

=item --verbose

Produce verbose output. You can specify this a number of times indicating
increased verbosity.

=item --dry-run

The command will print what it would have done, but won't change anything in
databases or on disk.

=item --version

Print the program version.

=item --help

Print a help message.

=item --debug

Producing debugging output. You can specify this a number of times indicating
increased debugging output volume.

=back

=head2 Using the Optconfig Module

=head3 Option Signatures

=over 4

=item config=s

The config file is a string. You don't have to do anything with it.

=item verbose+

The 'verbose' option value is a number indicating the verbosity level. You can
test this and/or use the L<vrb()> method.

=item debug+

The 'debug' option value is a number indicating the level. You can test this
and/or use the L<vrb()> method.

=item dry-run!

This is a boolean indicating whether a dry run is happening. You need to test
this when performing operations that would change persistent data. For example:

my $sth = $dbh->prepare("DROP TABLE $tab");
$opt->vrb(1, "Dropping table users");
$sth->execute() unless $opt->{'dry-run'};
$sth->finish();

=item version

Define a global variable $VERSION and Optconfig will print it out.

=item help

If your program has a pod page with a SYNOPSIS section, Optconfig will print
it out.

=back

=head3 Class Methods

=over 4

=item new($domain, \%options)

Parse command-line options and configuration files using $domain.

Each pair in the option hash is composed of an option specifer and a default
value. The option specifier is exactly that given in the L<Getopt::Long>
module.

=back

=head3 Object Methods

=over 4

=item vrb($level, $msg, ...)

Prints verbose output if the --verbose level is at or greater than the
verbosity mentioned. Thus, if you specify a level of 1, the message will be
printed if the user has specified C<--verbose>. If you specify a level of 3,
the user will have to pass C<--verbose --verbose --verbose> to see it.

=item dbg($level, $msg, ...)

Similar to L<vrb()>, but uses the value of the C<--debug> option and prints
a tag indicating the domain.

=back

=head1 BUGS

When consulting a configuration file, Optconfig should check the options for
adherence to the optspec, and it doesn't. This could result in unclear
failures in the program where the wrong type is configured (for example,
a scalar for a list).

There's no easy way to "empty out" an already-configured list or map value
from the configuration. In the example above, there's no combination of
command-line options that would result in a one-element list for the 'host'
option.

When Optconfig is merging the command-line options into the configuration,
it is affected by the type of the existing option value (from the configuration
file) whereas it should honor only the optspec.

=head1 AUTHOR

Jeremy Brinkley, E<lt>jbrinkley@proofpoint.comE<gt>
Python port by Eric Robbins, erobbins@evernote.com

=head1 SEE ALSO

=over 4

=item showconfig

=back

=cut
'''

################################################################################	
import sys,os,json,types

################################################################################	
class Optconfig(object):

	VERSION = 1.0

	standard_opts = {
		'config=s': False,
		'debug+':   0,
		'verbose+': 0,
		'version':  0,
		'help':     0,
		'dry-run!': 0 
	}
	_stuff = {}

	################################################################################	
	def croak(self, msg, err = ""):
		if len(err) > 0:
			print "%s: %s" % (msg, err)
		else
			print msg
		sys.exit(1)

	################################################################################	
	def _add_standard_opts(optspec):
		for i in standard_opts:
			if i not in optspec:
				optspec[i] = standard_opts[i]
		return optspec

	################################################################################	
	def __setitem__(self, key, val):
		self._stuff['key'] = val

	################################################################################	
	def __getitem__(self, key):
		return self._stuff['key']

	################################################################################	
	def __contains__(self, key):
		if key in self._stuff:
			return True
		return False

	################################################################################	
	def new(self, myclass, domain, submitted_optspec):
		self['_domain'] = domain
		self['_optspec'] = _add_standard_opts(submitted_optspec)
		cmdlineopt = {}
		defval = {}
		optspecs = []
	
		for optspec in submitted_optspec:
			val = submitted_optspec[optspec]
			optspecs.push(optspec)
			# TODO
			opt, dummy = optspec.split(/[=\!\+]/, $optspec, 2);
			self[opt] = val

		# TODO
		GetOptions($cmdlineopt, @optspecs);

		if "HOME" in os.environ:
			cfgfilepath = [ os.environ['HOME'] + '/.' + domain,
						'/opt/pptools/etc/' + domain + '.conf' ]
		else:
			cfgfilepath = [ '/opt/pptools/etc/' + domain + '.conf' ]

		self['_config'] = False
		gotconfig = False;

		if config in cmdlineopt:
			gotconfig = self.read_config(cmdlineopt['config'], True)

		for file in cfgfilepath:
			self['_config'] = file
			rval = self.read_config(file, False)
			if gotconfig == False:
				gotconfig = rval

		if gotconfig == False:
			croak("no valid configuration file found")

		for opt in cmdlineopt:
			self.merge_cmdlineopt(opt, cmdlineopt[opt])

		# TODO - not really necessary but.. might be nice
		#$self->ocdbg(Data::Dumper->Dump([$self], ['optconfig']));

		if self['version']:
			print self.VERSION
			sys.exit(0)

		if self['help']:
			print myhelp
			sys.exit(0)

		return self

	################################################################################	
	def merge_cmdlineopt(self, opt, val):
	# This logic is based on the value of the existing (configured) option value
	# but it should be based on the type of the optspec. -jdb/20100812

		#self.ocdbg("->merge_cmdlineopt('$opt', " . _val($val));

		if opt in self:
			if type(self[opt]) == types.DictType or type(self[opt]) == types.ListType:
				if type(self[opt]) == types.DictType:
					if (type(val) == types.DictType:
						# Merge, at least one-level
						for i in val:
							self[opt][i] = val[i]
					else:
						# The value given is a simple scalar value, all I can
						# do is blow away the hash. Also, same consideration as
						# below with the configured array value and the passed-in
						# non-array value. -jdb/20100812
						self[opt] = val
				elif type(self[opt]) == types.ListType:
					if type(val) == types.ListType:
						# The command-line values get put in *front* of the configured
						# values.
						self[opt] = val + self[opt] 
					else:
						# This happens when the type of the optspec is NOT ...@, but
						# the configuration file has a list value for this option.
						# It shouldn't really happen. In this circumstance the right
						# thing to do is follow the optspec instead of the configuration
						# because the optspec is under the control of the programmer (so
						# the program will actually expect the option value to match it)
						# while the configuration comes from heck-know-where (and we
						# should probably complain if it doesn't match the optspec
						# anyway). -jdb/20100812
						self[opt] = val
				else:
					# It's a reference, but not a hash or array reference. Whuh?
					# Blast it away.
					self[opt] = val
			# else, not dict or list.. just overwrite it
			else:
				# Scalar value: override
				self[opt] = val
		else:
			# Not configured: normal set value
			self[opt] = val;

		return self[opt]

	################################################################################	
	# TODO: read_config should be cognizant of the option types, in particular
	# things like =s@.
	def read_config(self, file, death):
		try:
			f = open(file, "r")
		except IOError as e:
			if death:
				self.croak(file, e[1])
			else
				return

		text = "\n".join(f.readlines())
		f.close()
		obj = self._from_json(text)
		for i in obj:
			self[i] = obj{i}
		return obj

	################################################################################	
	def _from_json(str):
		return json.loads(str)

	################################################################################	
	def _to_json(obj):
		return json.dumps(obj)

	################################################################################	
	# TODO - not sure what this is for/where it is used/why it's here.
	#def hash(self):
	#
	#		newhash = { }
	#
	#		for my $key (keys %$self) {
	#   			$hash->{$key} = $self->{$key} unless $key =~ /^_/;
	#		}
	#
	#		return $hash;
	#
	################################################################################	
	def vrb(self, level, msg):
		if level <= self.verbose:
			print "\n".join(msg)

	################################################################################	
	def dbg(self, level, msg):
 		if level <= self.debug:
			dbgstr = "\nDBG(%s)" % (self._domain)
			print "%s: %s" % (dbgstr, dbgstr.join(msg))

	################################################################################	
	def ocdbg(arg):
	# This debugging is controlled by an environment variable, because
	# it's really orthogonal to the use of a 'debug' option in the constructor
	# or something like that. -jdb/20100812
		if os.environ["OPTCONFIG_DEBUG"]:
			print "\nDBG(Optconfig)".join(arg)

	################################################################################	
	# end Optconfig class