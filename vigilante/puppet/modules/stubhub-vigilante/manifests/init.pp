class stubhub-vigilante {
  File {
    owner => root,
    group => root,
    mode => 644,
  }
  
  
 file { '/usr/local/bin/phaktor.py':
    ensure => file,
    mode => 755,
    source => 'puppet:///modules/stubhub-vigilante/phaktor.py',
  }
  
  file { '/usr/local/bin/phaktor':
    ensure => link,
    target => '/usr/local/bin/phaktor.py',
  }

  file { '/nas/reg/log/jiralab/vigilante/facts.ftr':
    ensure => file,
    source => 'puppet:///modules/stubhub-vigilante/facts.ftr',
  }

  file { '/nas/reg/log/jiralab/vigilante/auditor':
    ensure => directory,
  }
  
  cron { "phaktor":
	user  => root,
	minute => [ fqdn_rand(30),fqdn_rand(30) + 30 ],
    command => "phaktor -c /nas/reg/log/jiralab/vigilante/facts.ftr -r /nas/reg/log/jiralab/vigilante/auditor ",  
    require => File[ '/nas/reg/log/jiralab/vigilante/facts.ftr'],

  }

}
include stubhub-vigilante