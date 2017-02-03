#phoenix

```
create table report_data_100(
    report_id varchar not null,
    statdate varchar not null,
    dim3 varchar not null,
    dim4 varchar not null,
    dim5 varchar not null,
    dim6 varchar not null,
    dim7 varchar not null,
    dim8 varchar not null,
    dim9 varchar not null,
    dim10 varchar not null,
    dim11 varchar not null,
    dim12 varchar not null,
    dim13 varchar not null,
    dim14 varchar not null,
    dim15 varchar not null,
    dim16 varchar not null,
    dim17 varchar not null,
    dim18 varchar not null,
    dim19 varchar not null,
    dim20 varchar not null,
    valueArray double array,
    dimNameArray varchar array,
    constraint pk primary key (report_id,statdate,dim3,dim4,dim5,dim6,dim7,dim8 ,dim9,dim10,dim11,dim12,dim13,dim14,dim15,dim16,dim17,dim18,dim19,dim20)
);

```
