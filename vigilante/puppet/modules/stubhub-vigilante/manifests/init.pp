class stubhub-vigilante {
  File {
    owner => root,
    group => root,
    mode => 644,
  }

  file { '/nas/reg/log/jiralab/vigilante/facts.ftr':
    ensure => file,
    #source => 'puppet:///modules/stubhub-vigilante/files/facts.ftr',
  }

  file { '/nas/reg/log/jiralab/vigilante/auditor':
    ensure => directory,
    #source => 'puppet:///modules/stubhub-vigilante/files/facts.ftr',
  }
  
  exec { "phaktor":
    command => "phaktor -c /nas/reg/log/jiralab/vigilante/facts.ftr -r /nas/reg/log/jiralab/vigilante/auditor ",
    path    => "/nas/reg/bin/jiralab/",
    logoutput => true,

  }

}