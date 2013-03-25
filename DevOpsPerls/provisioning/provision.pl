#!/usr/bin/perl

# -----------------------------------------------------------------------
#
# $Id: //internal/reg/main/fsroot/nas/reg/bin/provision#20 $
#
# $DateTime: 2013/03/15 06:41:54 $
#
# $Change: 183413 $
#
# $Author: minjzhang $
#
# -----------------------------------------------------------------------

use strict;
use warnings;

use lib '/nas/reg/lib/perl';

use REG::Util qw( shell );
use File::Basename;
use Config::General;
use File::Find;
use Getopt::Long qw( :config no_ignore_case bundling );
use Log::Transcript;
use Readonly;
use English;
use Data::Dumper;
use REG::Constants qw( :all_constants );

++$|;

sub clean_die ( @ );
sub verify ( $$ );

     # install signal handlers
#$SIG{ HUP }  = \&catch_signal;
#$SIG{ INT }  = \&catch_signal;
#$SIG{ TERM } = \&catch_signal;

########################################################################
# globals
########################################################################
$ENV{ PATH } = "/sbin:/bin:/usr/bin/:/sbin:/bin:/nas/reg/bin";
my $pgm            = basename $0;
my @ORIGINAL_ARGV  = @ARGV;
my $BATCHMODE      = not ( -t );
my $SSH            = "ssh $NON_INTERACTIVE_SSH_OPTIONS";
my $environment    = "srwd63";
my $serverList;
my %expected_servers;
my %servers;
my $help           =  0;
my $verbose        =  0;
my $puppetServer   =  "srwd00pup001.stubcorp.dev";
my $ipmiServer     =  "srwd00mgt001.stubcorp.dev";
my $sshTimeOut     =  10;
my %allTasks       = ( dns             => "provision dns",
                       reimage         => "restart the servers",
                     );
my @tasks          = ( "dns", "reimage" );

########################################################################
sub help {
########################################################################
  logecho "
usage: $pgm options tasks

required options:
  -e,--environment         Environment.

other options:
  -s,--servers             Servers. Multiple servers separated by comma ','.
  -h,--help                List usage.
  -t,--time-out            Time Out.
  -v,--verbose             Select verbose output mode  incrementally.

examples:
  $pgm -e srwd63
  $pgm -e srwd63 dns
  $pgm -e srwd63 @tasks
  $pgm -e srwd63 -s srwd63pay001.srwd63.com reimage

";
  logecho "\ntasks:\n";
  foreach my $task ( sort keys %allTasks ) {
    logecho "  $task:";
    logecho "          $_" foreach (split (/\n/, $allTasks{$task}));
  }
  exit 0;
}

########################################################################
sub init {
########################################################################
       # in batchmode, Log::Transcript needs this information so that it
       # can send session transcripts when necessary
  if ( $BATCHMODE ) {
    Log::Transcript::setenv(
      envelope_from         => $RELMGT_EMAIL,
      message_from          => $RELMGT_EMAIL,
      reply_to              => $RELMGT_EMAIL,
      transcript_recipients => $RELMGT_EMAIL,
    );
  } # if

  unless ( GetOptions (
             'e|env=s'            => \$environment,
             's|servers=s'        => \$serverList,
             'h|help'             => \$help,
             't|time-out=s'       => \$sshTimeOut,
             'v|verbose+'         => \$verbose,
             )
         )
  {
    help;
  }

  @tasks = @ARGV if @ARGV;
  help if $help or not $environment;


  $verbose && logecho "init: command:      $pgm @ORIGINAL_ARGV";
  $verbose && logecho "init: tasks:        @tasks";
  if ( defined $serverList ) {
    @expected_servers{ split /,/, $serverList } = ();
    $verbose && logecho "init: tasks:        $serverList";
  }
  $verbose && logecho "init: verbose:      $verbose";
  $verbose && logecho "init: ssh time out: $sshTimeOut";

}

########################################################################
sub verifyCobblerEnabled($){
########################################################################
  my $env = shift;

  $verbose and logecho "verifyCobblerEnabled: env: $env";
  my ($status, @output) = sshCmd(1, $puppetServer, "sudo cobbler system find --name=$env");
  my $count = 0;

  if ( defined $serverList ) {
    foreach my $line (@output) {
      $line =~ s/\s*(\S*)\s*/$1/;
      if ( exists $expected_servers{$line} ) {
        $servers{$1}="WAITING";
        $verbose && logecho "verifyCobblerEnabled: $1";
        $count++;
      }
    }
    foreach my $expected_server (keys %expected_servers) {
      if ( not exists $servers{$expected_server} ) {
        logecho "verifyCobblerEnabled: Cobbler knows nothing about server $expected_server";
      }
    }
  } else {
    foreach my $line (@output) {
      if ($line =~ /\s*($environment\S*)\s*/) {
        $servers{$1}="WAITING";
        $verbose && logecho "verifyCobblerEnabled: $1";
        $count++;
      }
    }
  }

  logecho "verifyCobblerEnabled: $count servers found for $environment";

  logdie "verifyCobblerEnabled: Cobbler knows nothing about $environment" unless $count;

}

########################################################################
sub runCmd($$) {
########################################################################
  my $logOnFailure = shift;
  my $cmd = shift;

  logecho "runCmd: cmd: $cmd" if ($verbose>1);
  my @output = `$cmd`;
  my $status = $? >> 8;
  if ($verbose>1 or $status ) {logecho "runCmd: output: $_" foreach (@output);}
  return ($status, @output);
}

########################################################################
sub sshCmd($$$) {
########################################################################
  my $logOnFailure = shift;
  my $machine = shift;
  my $cmd = shift;
  return runCmd($logOnFailure, "$SSH -o ConnectTimeout=$sshTimeOut $machine $cmd");
}

########################################################################
sub systemLog($){
########################################################################
  my $s = shift;
  return sshCmd(1, $puppetServer, "logger -t 'provision[$$]' -- $s");
}

########################################################################
sub dns_task($) {
########################################################################
  my $env = shift;

  $verbose and logecho "dns_task: env: $env";
  my $cmd = "'C:\\stubs\\${env}-dns.bat'";
  my $host = "svcacctprov\@srwd00utl002";
  $verbose and logecho "host: $host";
  $verbose and logecho "cmd: $cmd";

  my ($status, @output) = sshCmd(1, $host, $cmd);
  $verbose && logecho "dns_task: $_" foreach (@output);
  my $failed=0;
  foreach my $line (@output) {
    if ($line =~ /ERROR/) {
      $failed++;
      logwarn "dns_task: $line";
    }
  }
  logdie("dns_task: $cmd failed") if $failed || $status;
}

########################################################################
sub verify($$){
########################################################################
  my $env = shift;
  my $trys = shift;
  my $delay = 150;

  logecho "----------------------------------------------------------";
  my $done=1;
  logecho "verify: env: $env ($trys)";
  logecho "verify: pausing for $delay seconds";
  sleep $delay;
  logecho "verify: reading $puppetServer:/var/log/messages";
  my ($status, @output) = sshCmd(1, $puppetServer, "sudo cat /var/log/messages");
  logdie "verify: can not read /var/log/messages $puppetServer" if $status;
  my $found=0;
  foreach my $line (@output) {
    next unless $found || $line =~ /provision\[$$\]/;
    $found=1;
    next unless $line =~ /puppet-master.*Compiled catalog for (${environment}\S+)/;
    my $server=$1;
    $verbose and logecho "verify: output: $server";
    $servers{$server}="DONE";
  }
  foreach my $server (sort keys %servers) {
    logecho "verify: server: $server: $servers{$server}";
    $done=0 if $servers{$server} eq "WAITING";
  }
  $verbose and logecho "verify: done: $done";
  $verbose and logecho "verify: trys: $trys";
  verify($env, $trys - 1) if $trys and not $done;
  logdie "verify: unable to verify all servers in $environment were reimaged" unless $trys or $done;
}

# -----------------------------------------------------------------------
#
# setNetBoot
#
# -----------------------------------------------------------------------
sub setNetBoot($){
    my $value = shift;

    $verbose and logecho "setNetBoot: value: $value";
    foreach my $server (keys %servers) {
        #if ($server =~ /srwe04/i) {
        #    if ($server =~ /abi|lcm|mch|lcx|brx|ech|cmi|bpm/) { next; }
        #}

        $verbose and logecho "setNetBoot: server: $server value: $value";
        my ($status, @output) = sshCmd(1, $puppetServer, "sudo cobbler system edit --name $server --netboot=$value");
        logdie "setNetBoot: Can not set netboot for $server via cobbler" if $status;
    }
}   # End of setNetBoot

########################################################################
# -----------------------------------------------------------------------
#
# resetPHYS
#
# -----------------------------------------------------------------------
sub resetPHYS($) {
    my $server = shift;
 

    $verbose and logecho "resetPHYS: env: $server";

    logecho "----------------------------------------------------------";
    $server =~ s/\./m1\./
    my ($status, @resetcmd) = sshCmd(1, $ipmiServer, "ipmitool -H $server -U ADMIN -P ADMIN -I lan chassis bootdev pxe"); 
    my ($status, @resetcmd) = sshCmd(1, $ipmiServer, "ipmitool -H $server -U ADMIN -P ADMIN -I lan power reset");

    logecho "----------------------------------------------------------";
}   # End of resetPHYS

########################################################################
# -----------------------------------------------------------------------
#
# stopVM(s)
#
# -----------------------------------------------------------------------
sub stopVM($) {
  my $process_server = shift;

  my $host = "svcacctprov\@srwd00wsh001";
  my $cmd = q{powershell  -psc '"C:\Program Files (x86)\VMware\Infrastructure\vSphere PowerCLI\vim.psc1"' -InputFormat None -F  '\stubs\stop.ps1' } . "'${process_server}'";
  $verbose and logecho "stopVM: cmd: $cmd";
  my ($status, @output) = sshCmd(1, $host, $cmd);
  $verbose && logecho "stop: $_" foreach (@output);
}

# -----------------------------------------------------------------------
#
# startVM(s)
#
# -----------------------------------------------------------------------
sub startVM($) {
  my $process_server = shift;

  my $host = "svcacctprov\@srwd00wsh001";
  my $cmd = q{powershell  -psc '"C:\Program Files (x86)\VMware\Infrastructure\vSphere PowerCLI\vim.psc1"' -InputFormat None -F  '\stubs\start.ps1' } . "'${process_server}'";
  $verbose and logecho "startVM: cmd: $cmd";
  my ($status, @output) = sshCmd(1, $host, $cmd);
  $verbose && logecho "start: $_" foreach (@output);
}


# -----------------------------------------------------------------------
#
# restartVM
#
# -----------------------------------------------------------------------
sub restartVM($) {
    my $env = shift;

    $verbose and logecho "restartVM: env: $env";

    logecho "----------------------------------------------------------";

    if ( defined $serverList ) {
      foreach my $server (keys %servers) {
        stopVM($server);
      }
      logecho "stop: sleeping 120 seconds";
      sleep 120;
    } else {
    	
      stopVM("${env}*");
      logecho "stop: sleeping 120 seconds";
      sleep 120;
    }

    logecho "----------------------------------------------------------";

    if ( defined $serverList ) {
      foreach my $server (keys %servers) {
        startVM($server);
      }
      logecho "start: sleeping 120 seconds";
      sleep 120;
    } else {
      startVM("${env}*");
      logecho "start: sleeping 120 seconds";
      sleep 120;
    }

    logecho "----------------------------------------------------------";
}   # End of restartVM

########################################################################
# -----------------------------------------------------------------------
#
# restartPHYS
#
# -----------------------------------------------------------------------
sub restartPHYS($) {
    my $env = shift;

    $verbose and logecho "restartPHYS: env: $env";

    logecho "----------------------------------------------------------";

    if ( defined $serverList ) {
      foreach my $server (keys %servers) {
        resetPHYS($server);
      }
    } else {
      my ($status, @physicals) = sshCmd(1, $puppetServer, "/nas/reg/bin/physicals $env");
      foreach my $physical = (@physicals) {
      	resetPHYS(chomp($physical));
      }
      logecho "stop: sleeping 120 seconds";
      sleep 120;
    }


    logecho "----------------------------------------------------------";
}   # End of restartPHYS

########################################################################
sub reimage_task($){
########################################################################
  my $env = shift;

  systemLog("Reimaging $environment");
  verifyCobblerEnabled($environment);
  setNetBoot("Y");
  restartVM($env);
  if ( $env =~/srwe/){
  	restartPHYS($env)
  }
  logecho "reimage: sleeping 2 minutes";
  sleep 120;
  setNetBoot("N");
  verify($env, 20);
  logecho "reimage_task: removing /nas/reg/relmgt/.ssh/known_hosts";
  system "/bin/rm -rf /nas/reg/relmgt/.ssh/known_hosts";
  logecho "reimage: all $env servers are communicating with $puppetServer";
  logecho "reimage: sleeping 2 minutes";
  sleep 120;
}

init;
my $t1 = time();
foreach my $task (@tasks) {
  my $t2 = time();
  logecho "----------------------------------------------------------";
  logecho "task: $task";
  my $sub = "${task}_task";

  {no strict 'refs'; &$sub ($environment); use strict 'refs';}
}


exit 0;
