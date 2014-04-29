class stubhub-vigilante (
    $phaktordepth = '10',
    $phaktor_exe = '/usr/local/bin/phaktor.py',
    $phaktor_cfg = '/nas/reg/log/jiralab/vigilante/facts.ftr',
    $phaktor_dir = '/nas/reg/log/jiralab/vigilante/auditor',
    $phaktor_sched_hour = [ fqdn_rand(4), 6+fqdn_rand(5), 12+fqdn_rand(5), 18+fqdn_rand(5) ],
){

  File {
    owner => root,
    group => root,
    mode  => 0644,
    }

  file { $phaktor_exe :
    ensure => file,
    mode   => '0755',
    source => 'puppet:///modules/stubhub-vigilante/bin/phaktor.py',
  }

  file { '/usr/local/bin/phaktor':
    ensure => link,
    target => $phaktor_exe,
  }

  file { $phaktor_cfg :
    ensure => file,
    source => 'puppet:///modules/stubhub-vigilante/etc/facts.ftr',
  }

  file { $phaktor_dir :
    ensure => directory,
  }


  cron { 'phaktor':
    user    => root,
    minute  => fqdn_rand(60),
    hour    => $phaktor_sched_hour,
    command => "phaktor -c ${phaktor_cfg} -r ${phaktor_dir} -d ${phaktordepth}",
    require => File[ $phaktor_cfg, $phaktor_cfg ],

  }

}
include stubhub-vigilante
