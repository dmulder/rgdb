#
# spec file for package rgdb
#

Name:		rgdb
Version:	1.3
Release:	1
License:	MIT
Summary:	Remote debugging using gdb
Url:		http://www.github.com/DavidMulder/rgdb
Group:		Development/Tools/Debuggers
Source:		%{name}-%{version}.tar.gz
Requires:	python-pyzmq
Requires:	python-paramiko

%description
Remote debugging using gdb with graphical code breaks and stepping.

%prep
%setup -q

%build

%install
%{__install} -D -m 0755 rgdb.py $RPM_BUILD_ROOT/usr/%_lib/rgdb/rgdb.py
%{__install} -D -m 0755 rgdb_ui.py $RPM_BUILD_ROOT/usr/%_lib/rgdb/rgdb_ui.py
%{__mkdir} -p $RPM_BUILD_ROOT/%{_bindir}
%{__ln_s} /usr/%_lib/rgdb/rgdb.py $RPM_BUILD_ROOT/%{_bindir}/rgdb
%{__ln_s} /usr/%_lib/rgdb/rgdb_ui.py $RPM_BUILD_ROOT/%{_bindir}/rgdb_ui
%{__install} -D -m 0644 README $RPM_BUILD_ROOT/%{_defaultdocdir}/rgdb/README

%clean
%{__rm} -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
/usr/%_lib/rgdb
/usr/%_lib/rgdb/rgdb.py
/usr/%_lib/rgdb/rgdb_ui.py
%{_bindir}/rgdb
%{_bindir}/rgdb_ui
%{_defaultdocdir}/rgdb
%{_defaultdocdir}/rgdb/README

