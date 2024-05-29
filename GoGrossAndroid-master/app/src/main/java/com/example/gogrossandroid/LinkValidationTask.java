package com.example.gogrossandroid;

import android.os.AsyncTask;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.lang.ref.WeakReference;
import java.net.HttpURLConnection;
import java.net.URL;

public class LinkValidationTask extends AsyncTask<String, Void, Boolean> {

    private WeakReference<DeepLinkRegistration> activityReference;
    private String link;

    LinkValidationTask(DeepLinkRegistration activity, String link) {
        activityReference = new WeakReference<>(activity);
        this.link = link;
    }


    @Override
    protected Boolean doInBackground(String... strings) {
        if (strings.length == 0) return false;
        String link = strings[0];
        try {
            URL url = new URL(link.substring(0,link.length()-4) + "is_gogross");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            connection.setRequestProperty("Content-Type", "application/json");

            int responseCode = connection.getResponseCode();

            if (responseCode == HttpURLConnection.HTTP_OK) {
                BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                reader.close();

                String responseBody = response.toString();
                return "Ich bims, 1 gogross".equals(responseBody);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    @Override
    protected void onPostExecute(Boolean isValid) {
        DeepLinkRegistration activity = activityReference.get();
        if (activity == null || activity.isFinishing()) return;
        try {
            if (isValid) {
                activity.saveContent();
                activity.changeActivity(link);
            } else {
                // Don't change activity if the link is invalid
                DeepLinkRegistration.displayErrorMessage("Invalid Link, try again");
            }
        } catch (Exception e) {
            e.printStackTrace();
            activity.displayErrorMessage("An error occurred, please try again later");
        }
    }
}
