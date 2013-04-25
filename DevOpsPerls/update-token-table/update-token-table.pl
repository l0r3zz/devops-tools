#!/usr/bin/perl

use warnings;
use strict;

use lib '/nas/reg/lib/perl';

use File::Basename;
use File::Path;
use Getopt::Long qw( :config no_ignore_case bundling );
use List::Util qw( first );
use Log::Transcript;
use Readonly;
use REG::P4::Util qw(
                      $P4OPTS
                      client_exists
                      delete_dynamic_client
                      dynamic_client
                      get_lines_from_perforce_file
                      p4cmd
                    );
use REG::Util qw(
                  make_lock_directory
                  refchk
                  ql
                  shell
                  validate_env_identifier
                  validate_process_owner
                );
use REG::Constants qw( :all_constants );

sub clean_die ( @ );

     # install signal handlers
$SIG{ HUP }  = \&catch_signal;
$SIG{ INT }  = \&catch_signal;
$SIG{ TERM } = \&catch_signal;

$ENV{ PATH } = "$DEFAULT_SAFE_PATH:/usr/local/bin";

Readonly my $pgm => basename $0;

     # capture command line information and create a string
     # representing the original arguments to this program
Readonly my @ORIGINAL_ARGV => @ARGV;
Readonly my $ORIGINAL_ARGV => ql( @ARGV );

     # will be made to hold information on a dynamically created
     # perforce client if we create one
my $dynamic_perforce_client;

Readonly my $TOKEN_TABLE_DIRECTORY_DEPOT_PATH => '//internal/dev/properties/tokenization';

Readonly my $TOKEN_TABLES => {
              'env-based'                           => "$TOKEN_TABLE_DIRECTORY_DEPOT_PATH/token-table-env-based",
              'token-table-env-based'               => "$TOKEN_TABLE_DIRECTORY_DEPOT_PATH/token-table-env-based",
              'env-stubhub-properties'              => "$TOKEN_TABLE_DIRECTORY_DEPOT_PATH/token-table-env-stubhub-properties",
              'token-table-env-stubhub-properties'  => "$TOKEN_TABLE_DIRECTORY_DEPOT_PATH/token-table-env-stubhub-properties",
            };

Readonly my $TOKEN_TABLE_CHOICES => "{ '" . join( q{', '}, sort keys %$TOKEN_TABLES ) . "' }";

     # parent of the lock directory we'll attempt to create
Readonly my $PROGRAM_LOCK_TREE => $NAS_LOCK_TREE;

     # parameters used when we attempt to create a lock directory
Readonly my $MAX_LOCK_ATTEMPTS => 6;
Readonly my $LOCK_ATTEMPTS_INTERVAL => 10;

     # if and when we succeed in creating a lock directory, we'll set
     # this to true.  when we do clean up, we only want to release the
     # lock if we were the process that acquired it.
my $we_acquired_a_run_lock = $FALSE;

     # usage statement.  a "here document".
my $usage = << "_END_OF_USAGE_";
usage: $pgm options

required options:

  -e,--envid Environment-ID        Modify values in the section for environment
                                   Environment-ID

  -r,--release-template path       path to release template file

  -r,--replacement-string String   Indicate that String is the replacement
                                   string.  The replacement string may not
                                   contain newlines.

  -s,--search-string String        Indicate that String is the string to be
                                   replaced.  String cannot contain newlines.
                                   This program does not change values that are
                                   here documents.

  -t,--token-table Token-Table     Select token table to modify.  Choices are:
                                     $TOKEN_TABLE_CHOICES

other options:
  -c,--comments Text               Include Text in the change list description.
                                   Newlines are not allowed in comments.

  -h,--help                        List usage

  -v,--verbose                     Increase level of verbosity.  Default level
                                   is zero (non-verbose output).  Each instance
                                   of this option increases the level by one.
                                   For example, "--verbose --verbose" or "-vv"
                                   would set the verbosity level to two.
_END_OF_USAGE_

     # if stdin is not associated with a tty, we're in batch (i.e.,
     # non-interactive) mode
Readonly my $BATCHMODE => not ( -t );

     # in batchmode, Log::Transcript needs this information so that it
     # can send session transcripts when necessary
if ( $BATCHMODE ) {
  Log::Transcript::setenv(
    envelope_from         => $RELMGT_EMAIL,
    message_from          => $RELMGT_EMAIL,
    reply_to              => $RELMGT_EMAIL,
    transcript_recipients => $REG_MESSAGES_EMAIL,
  );
} # if

not @ARGV and logdie $usage;

     # usage message if we get a command line with no args
my $optargs;
if ( not GetOptions (
           'c|comments=s'           => \$optargs->{ comments },
           'e|envid=s'              => \$optargs->{ envid },
           'h|help'                 => \$optargs->{ help },
           'r|replacement-string=s' => \$optargs->{ replacement_string },
           'R|release-template=s'   => \$optargs->{ release_template },
           'd|service-name=s'       => \$optargs->{ service_name },
           'R|release=s'            => \$optargs->{ release },
           's|search-string=s'      => \$optargs->{ search_string },
           't|token-table=s'        => \$optargs->{ token_table },
           'v|verbose+'             => \$optargs->{ verbose },
         )
   )
{
       # otherwise log the command line args and die, sending email in
       # batchmode
  $BATCHMODE and logdie "cmdline => $ORIGINAL_ARGV\n$usage";
  die "cmdline => $ORIGINAL_ARGV\n$usage";
} # if

     # user gave help option
$optargs->{ help } and warn $usage and exit 0;

Readonly my $ENVID => ( defined $optargs->{ envid } ? lc $optargs->{ envid } : logdie "missing --envid\n$usage" );
Readonly my $RELEASE_TEMPLATE => ( defined $optargs->{ release_template } ? lc $optargs->{ release_template } : logdie "missing --release-template\n$usage" );
Readonly my $DBSN => ( defined $optargs->{ service_name } ? lc $optargs->{ service_name } : logdie "missing --service-name\n$usage" );

Readonly my $TOKEN_TABLE_ID => ( defined $optargs->{ token_table } ? lc $optargs->{ token_table } : logdie "missing --token-table\n$usage" );
Readonly my $TOKEN_TABLE => $TOKEN_TABLES->{ $TOKEN_TABLE_ID };

Readonly my $SEARCH_STRING => $optargs->{ search_string };
not defined $SEARCH_STRING and logdie "missing --search-string\n$usage";
$SEARCH_STRING eq $EMPTY_STRING and clean_die "search string => ''; empty search string is not allowed";

Readonly my $REPLACEMENT_STRING => $optargs->{ replacement_string };
not defined $REPLACEMENT_STRING and logdie "missing --replacement-string\n$usage";
$REPLACEMENT_STRING =~ m{ \n }xms and clean_die "replacement string ", ql( $REPLACEMENT_STRING ), " contains a newline";

Readonly my $COMMENTS => ( defined $optargs->{ comments } ? $optargs->{ comments } : $EMPTY_STRING );
$COMMENTS =~ m{ \n }xms and clean_die "comments => ", ql( $COMMENTS ), " contain a newline";

not first { $TOKEN_TABLE_ID eq $_ } keys %$TOKEN_TABLES and logdie "token table => '$TOKEN_TABLE_ID': not in $TOKEN_TABLE_CHOICES";

validate_env_identifier( $ENVID );

     # bail if not running as recommended user
Readonly my $PROGRAM_USER => 'relmgt';
validate_process_owner({ username => $PROGRAM_USER });

Readonly my $VERBOSE => ( defined $optargs->{ verbose } ? $optargs->{ verbose } : 0 );

Readonly my %SHELL_SHOWOPTS => (
              show_description => $VERBOSE,
              show_command     => $VERBOSE > 1,
              show_output      => $VERBOSE > 2,
            );

Readonly my $LOCK_DIRECTORY => "$PROGRAM_LOCK_TREE/${pgm}--$TOKEN_TABLE_ID";

make_lock_directory({
  lock_directory => $LOCK_DIRECTORY,
  max_attempts   => $MAX_LOCK_ATTEMPTS,
  interval       => $LOCK_ATTEMPTS_INTERVAL,
  verbose        => $VERBOSE,
}) or clean_die "can't acquire a run lock; made $MAX_LOCK_ATTEMPTS",
                " attempt(s) $LOCK_ATTEMPTS_INTERVAL seconds apart to",
                " create lock directory ' $LOCK_DIRECTORY'";
$we_acquired_a_run_lock = $TRUE;

$P4OPTS = "-u build -p $PERFORCE_DEFAULT_SERVER_SRW:$PERFORCE_DEFAULT_PORT_NUMBER";

my $dynamic_default_client_was_created = $FALSE;

$VERBOSE and logecho "creating dynamic perforce client for default instance";
$dynamic_perforce_client = dynamic_client({
                             depot   => 'depot',
                             verbose => $VERBOSE,
                           });
$dynamic_default_client_was_created = $TRUE;

Readonly my $CLIENT_NAME_DEFAULT_DYNAMIC => $dynamic_perforce_client->{ Client };

$P4OPTS = "-u build -p $PERFORCE_DEFAULT_SERVER_SRW:$PERFORCE_DEFAULT_PORT_NUMBER -c $CLIENT_NAME_DEFAULT_DYNAMIC";

Readonly my $TOKEN_TABLE_LINES => get_token_table_lines();
perform_simple_validation_of_token_table( $TOKEN_TABLE_LINES );

my $processed_token_table = process_token_table();

update_perforce( $processed_token_table );

exit 0;

END {
  cleanup();
  Log::Transcript::send_transcript();
}

#-----------------------------------------------------------------------
     # perform cleanup before ending program
sub cleanup {
  my $func = ( caller 0 )[ 3 ];

       # cleanup dynamic perforce client if we created one and it exists
  if ( defined $dynamic_perforce_client ) {
    revert_files();

    $VERBOSE and logecho "deleting dynamic perforce client $dynamic_perforce_client->{ Client }";
    delete_dynamic_client({
      client       => $dynamic_perforce_client,
      p4opts       => $P4OPTS,
      keep_files   => $FALSE,
    });
  } # if

  $we_acquired_a_run_lock and release_run_lock();

  return;
} # cleanup

#-----------------------------------------------------------------------
     # handle signals; print signal name and then cleanly die
sub catch_signal {
  my $signame = shift;
  clean_die "caught SIG$signame";
} # catch_signal

#-----------------------------------------------------------------------
     # perform cleanup and call logdie() with any args
sub clean_die ( @ ) {
  my $func = ( caller 0 )[ 3 ];

  cleanup();

       # now fall on our sword...
  logdie( @_ );

  return;
} # clean_die

#-----------------------------------------------------------------------
     ### THIS SUBROUTINE CALLED BY cleanup() so don't clean_die() in it
sub revert_files {
  my $func = ( caller 0 )[ 3 ];

  not client_exists( $dynamic_perforce_client->{ Client } ) and return;

  my $cmd = p4cmd( qq{opened $dynamic_perforce_client->{ Root }/...} );
  my $description = "checking for open files in dynamic perforce client";
  my $results = shell({ stderr_to_null => $TRUE, command  => $cmd, description => $description, %SHELL_SHOWOPTS });
  if ( defined $results->{ error } ) {
    logwarn "$func(): $results->{ error }\n";
    return;
  } # if

  my $status = $results->{ status };
  $status != $SHELL_TRUE
    and logwarn "$func(): cmd returned non-zero status ($status);",
                " cmd => '$cmd'; output => '$results->{ results }'";

  my $opened_files = [ split /\n/, $results->{ results } ];

       # nothing to revert
  $opened_files->[ 0 ] =~ m{ file\(s\) \s+ not \s+ opened \s+ on \s+ this \s+ client }xms and return;

  $cmd = p4cmd( qq{revert $dynamic_perforce_client->{ Root }/...} );
  $description = "reverting perforce client files";
  $results = shell({ command => $cmd, description => $description, %SHELL_SHOWOPTS });
  if ( defined $results->{ error } ) {
    logwarn "$func(): $results->{ error }\n";
    return;
  } # if

  $status = $results->{ status };
  $status != $SHELL_TRUE
    and logwarn "$func(): cmd returned non-zero status ($status);",
                " cmd => '$cmd'; output => '$results->{ results }'";
  return;
} # revert_files

#-----------------------------------------------------------------------
     # if (and only if) we acquired a lock, release the lock by
     # recursively removing the lock directory and its contents
sub release_run_lock {
  my $func = ( caller 0 )[ 3 ];

       # only release the lock if we acquired it!  we don't want to kill
       # another process' lock!
  not $we_acquired_a_run_lock and return;

  eval { rmtree $LOCK_DIRECTORY; };
  if ( $@ ) {

         # SINCE THIS SUBROUTINE IS CALLED BY clean_die(), USE logdie()
         # HERE TO PREVENT INFINITE RECURSION!
         # SINCE THIS SUBROUTINE IS CALLED BY clean_die(), USE logdie()
         # HERE TO PREVENT INFINITE RECURSION!
         # SINCE THIS SUBROUTINE IS CALLED BY clean_die(), USE logdie()
         # HERE TO PREVENT INFINITE RECURSION!
    logdie "error occurred during attempt to release lock by",
           " deleting lock directory '$LOCK_DIRECTORY': $@";
  } # if

  else {
    $VERBOSE and logecho "removed lock directory '$LOCK_DIRECTORY'";
  } # if

  return;
} # release_run_lock

#-----------------------------------------------------------------------
sub get_token_table_lines {
  my $func = ( caller 0 )[ 3 ];
  my $lines = get_lines_from_perforce_file({
                p4opts => $P4OPTS,
                perforce_url => "perforce:$TOKEN_TABLE",
              });
  return $lines;
} # get_token_table_lines

#-----------------------------------------------------------------------
sub perform_simple_validation_of_token_table {
  my $func = ( caller 0 )[ 3 ];

  not defined( my $token_table_lines = shift ) and clean_die "$func(): \$token_table defined";

  refchk( $token_table_lines, qw( ARRAY  token_table_lines ));

  not first { $_ =~ m{ \A \s* <token-metadata> }xms } @$token_table_lines
    and clean_die "$func(): can't find <token-metadata> tag; is this a token table?";

  not first { $_ =~ m{ \A \s* <token-defaults> }xms } @$token_table_lines
    and clean_die "$func(): can't find <token-defaults> tag; is this a token table?";

  return;
} # perform_simple_validation_of_token_table

#-----------------------------------------------------------------------
sub process_token_table {
  my $func = ( caller 0 )[ 3 ];

  my $processed_lines = [];

  my $beginning_line_number;
  my $ending_line_number;

  my $line_number = 0;
  for my $line ( @$TOKEN_TABLE_LINES ) {
    ++$line_number;
    $line =~ m{ \A \s* <$ENVID> \s* \z }xms and $beginning_line_number = $line_number;
    $line =~ m{ \A \s* </$ENVID> \s* \z }xms and $ending_line_number = $line_number;
  } # for

  not defined $beginning_line_number and die "can't find beginning of section <$ENVID> in token table '$TOKEN_TABLE'";
  not defined $ending_line_number and die "can't find end of section <$ENVID> in file '$TOKEN_TABLE'";

  my $begin_index = $beginning_line_number - 1;
  my $end_index = $ending_line_number - 1;

  if ( $begin_index - 1 >= 0 ) {
    for my $index ( 0 .. $begin_index - 1 ) {
      my $line = $TOKEN_TABLE_LINES->[ $index ];
      push @$processed_lines, "$line";
    } # for
  } # if

  INDEX:
  for my $index ( $begin_index .. $end_index ) {
    my $line = $TOKEN_TABLE_LINES->[ $index ];

         # if we don't get a name-value pair line...
    if ( $line !~ m{ \A ( \s* ) ( \S+ ) \s* = \s* ( .* ) }xms ) {
      push @$processed_lines, "$line";
      next INDEX;
    } # if

         # skip here document initial lines
    if ( $line =~ m{ \A ( \s* ) ( \S+ ) \s* = \s* << ( .* ) }xms ) {
      push @$processed_lines, "$line";
      next INDEX;
    } # if

    $line =~ m{ \A ( \s* ) ( \S+ ) \s* = \s* ( .* ) }xms;
    my ( $leading_whitespace, $name, $value ) = ( $1, $2, $3 );

    not defined $leading_whitespace and $leading_whitespace = $EMPTY_STRING;

         # strip any trailing whitespace
    $value =~ s{ \s+ \z }{}xms;

    if ( $value =~ m{ \Q$SEARCH_STRING\E }xms ) {
      ( my $modified_value = $value ) =~ s{ \Q$SEARCH_STRING\E }{$REPLACEMENT_STRING}gxms;
      push @$processed_lines, "${leading_whitespace}$name = $modified_value";
    } # if

    else {
      push @$processed_lines, "$line";
    } # if
  } # for

  if ( $end_index + 1 <= $#$TOKEN_TABLE_LINES ) {
    for my $index ( $end_index + 1 .. $#$TOKEN_TABLE_LINES ) {
      my $line = $TOKEN_TABLE_LINES->[ $index ];
      push @$processed_lines, "$line";
    } # for
  } # if

  return $processed_lines;
} # process_token_table

#-----------------------------------------------------------------------
sub update_perforce {
  my $func = ( caller 0 )[ 3 ];

  not defined( my $processed_token_table = shift ) and clean_die "$func(): \$processed_token_table undefined";
  refchk( $processed_token_table, qw( ARRAY  processed_token_table ));

  my $cmd = p4cmd( "sync $TOKEN_TABLE" );
  my $description = "sync'ing token table";
  my $results = shell({ command => $cmd, description => $description, %SHELL_SHOWOPTS });
  defined $results->{ error } and logdie "$func(): $results->{ error }";
  my $status = $results->{ status };
  $status != $SHELL_TRUE
    and logdie "$func(): cmd returned non-zero status ($status); cmd => '$cmd'; output => '$results->{ results }'";
  $results->{ results } =~ m{ no \s+ such \s+ file }xms and clean_die "cmd => $cmd; output => '$results->{ results }'";

  ( my $token_table_client_path = $TOKEN_TABLE ) =~ s{ \A // }{}xms;
  $token_table_client_path = "$dynamic_perforce_client->{ Root }/$token_table_client_path";

  $cmd = p4cmd( "edit $token_table_client_path" );
  $description = "opening token table for edit in dynamic perforce client";
  $results = shell({ command => $cmd, description => $description, %SHELL_SHOWOPTS });
  defined $results->{ error } and logdie "$func(): $results->{ error }";
  $status = $results->{ status };
  $status != $SHELL_TRUE
    and logdie "$func(): cmd returned non-zero status ($status); cmd => '$cmd'; output => '$results->{ results }'";
  $results->{ results } !~ m{ opened \s+ for \s+ edit }xms and clean_die "cmd => $cmd; output => '$results->{ results }'";

  open my $FH, '>', $token_table_client_path
    or clean_die "$func(): can't open token table in dynamic perforce client ($token_table_client_path) for writing: $!";
  print { $FH } join( "\n", @$processed_token_table, $EMPTY_STRING );
  close $FH
    or logwarn "$func(): can't close token table in dynamic perforce client ($token_table_client_path) after writing: $!";

  ( my $args = $ORIGINAL_ARGV ) =~ s{,}{}gxms;

  my $LOGNAME = ( defined $ENV{ LOGNAME } ? $ENV{ LOGNAME } : '[env variable LOGNAME is not set]' );
  my $SUDO_USER = ( defined $ENV{ SUDO_USER } ? $ENV{ SUDO_USER } : '[env variable SUDO_USER is not set]' );

  my $change_list_description = << "_END_CHANGE_LIST_DESCRIPTION_";
changing values in <$ENVID>

LOGNAME   => '$LOGNAME'
SUDO_USER => '$SUDO_USER'

$COMMENTS

change generated by automation.  command line:
  $0 $args
_END_CHANGE_LIST_DESCRIPTION_

  $cmd = p4cmd( qq{submit -d "$change_list_description" $token_table_client_path} );
  $description = "submitting modified token table to perforce";
  $results = shell({ command => $cmd, description => $description, %SHELL_SHOWOPTS });
  defined $results->{ error } and logdie "$func(): $results->{ error }";
  $status = $results->{ status };

  my $results_lines = [ split /\n/, $results->{ results } ];

  my $no_files_to_submit_line;
  if ( $status != $SHELL_TRUE ) {
    $no_files_to_submit_line = first { $_ =~ m{ no \s+ files \s+ to \s+ submit }ixms } @$results_lines;
    if ( defined $no_files_to_submit_line ) {
       logecho $no_files_to_submit_line;
    } # if
    else {
      logdie "$func(): cmd returned non-zero status ($status); cmd => '$cmd'; output => '$results->{ results }'";
    } # if
  } # if

  if ( not defined $no_files_to_submit_line ) {
    my $change_submitted_line = first { $_ =~ m{ change .* submitted[.] }ixms } @$results_lines;
    not defined $change_submitted_line and clean_die "cmd => $cmd; output => '$results->{ results }'";

    $VERBOSE and defined $change_submitted_line and logecho $change_submitted_line;
  } # if

  return;
} # update_perforce

