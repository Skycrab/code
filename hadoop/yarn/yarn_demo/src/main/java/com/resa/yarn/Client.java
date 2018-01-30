/*
* Simple YARN Application Skeleton
* Copyright (C) 2015 George Piskas, Philémon Favrod
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation; either version 2 of the License, or
* (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License along
* with this program; if not, write to the Free Software Foundation, Inc.,
* 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
*
* Contact: geopiskas@gmail.com
*/


package com.resa.yarn;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.apache.hadoop.yarn.api.ApplicationConstants;
import org.apache.hadoop.yarn.api.records.ApplicationId;
import org.apache.hadoop.yarn.api.records.ApplicationReport;
import org.apache.hadoop.yarn.api.records.ApplicationSubmissionContext;
import org.apache.hadoop.yarn.api.records.ContainerLaunchContext;
import org.apache.hadoop.yarn.api.records.LocalResource;
import org.apache.hadoop.yarn.api.records.Resource;
import org.apache.hadoop.yarn.api.records.YarnApplicationState;
import org.apache.hadoop.yarn.client.api.YarnClient;
import org.apache.hadoop.yarn.client.api.YarnClientApplication;
import org.apache.hadoop.yarn.conf.YarnConfiguration;
import org.apache.hadoop.yarn.util.Records;

public class Client {

    private YarnConfiguration conf;

    public static void main(String[] args){
        System.out.println("Client: Initializing");
        try {
            new Client().run();
        } catch (Exception ex) {
            ex.printStackTrace();
        }
    }

    private void run() throws Exception {
        conf = new YarnConfiguration();

        // Create Yarn Client
        YarnClient client = YarnClient.createYarnClient();
        client.init(conf);
        client.start();

        // Create Application
        YarnClientApplication app = client.createApplication();

        // Create AM Container
        ContainerLaunchContext amCLC = Records.newRecord(ContainerLaunchContext.class);
        amCLC.setCommands(Collections.singletonList("$JAVA_HOME/bin/java"
                + " -Xmx256M"
                + " com.resa.yarn.AppMaster"
                + " 1>" + ApplicationConstants.LOG_DIR_EXPANSION_VAR + "/stdout"
                + " 2>" + ApplicationConstants.LOG_DIR_EXPANSION_VAR + "/stderr"));

        // Set AM jar
        LocalResource jar = Records.newRecord(LocalResource.class);
        Utils.setUpLocalResource(Utils.YARNAPP_JAR_PATH, jar, conf);
        amCLC.setLocalResources(Collections.singletonMap(Utils.YARNAPP_JAR_NAME, jar));

        // Set AM CLASSPATH
        Map<String, String> env = new HashMap<String, String>();
        Utils.setUpEnv(env, conf);
        amCLC.setEnvironment(env);

        // Set AM resources
        Resource res = Records.newRecord(Resource.class);
        res.setMemory(256);
        res.setVirtualCores(1);

        // Create ApplicationSubmissionContext
        ApplicationSubmissionContext appContext = app.getApplicationSubmissionContext();
        appContext.setApplicationName("YARNAPP");
        appContext.setQueue("default");
        appContext.setAMContainerSpec(amCLC);
        appContext.setResource(res);

        // Submit Application
        ApplicationId id = appContext.getApplicationId();
        System.out.println("Client: Submitting " + id);
        client.submitApplication(appContext);

        ApplicationReport appReport = client.getApplicationReport(id);
        YarnApplicationState appState = appReport.getYarnApplicationState();
        while (appState != YarnApplicationState.FINISHED
                && appState != YarnApplicationState.KILLED
                && appState != YarnApplicationState.FAILED) {
            Thread.sleep(1000);
            appReport = client.getApplicationReport(id);
            appState = appReport.getYarnApplicationState();
        }

        System.out.println("Client: Finished " + id + " with state " + appState);
    }

}
