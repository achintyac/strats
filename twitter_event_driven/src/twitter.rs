use serde::Deserialize;
use serde_json::{Value, Deserializer};
use reqwest::{header::CONTENT_TYPE, Client, Response};
use crate::io::write_tweet;

#[derive(Deserialize, Debug)]
pub struct TwtrApiConfig {
    pub twitter_api: String,
    pub twitter_secret_key: String,
    pub twitter_access: String,
    pub twitter_access_secret: String,
    pub twitter_bearer_token: String,
    pub file_path: String,
    pub file_path_hist: String,

}

#[derive(serde::Serialize, Deserialize, Debug)]
pub struct Tweet {
    pub data: String,
    pub id: String,
    pub username: String,
    pub time: String,
    pub rule_tag: String,
}

#[derive(serde::Serialize, Deserialize, Debug)]
pub struct User {
    pub user_id: String,
    pub screen_name: String,
}

impl Tweet {
    pub fn into_array(&self) -> [&String; 5] {[&self.data, &self.id, &self.username, &self.time, &self.rule_tag]}
}

#[derive(serde::Serialize, Deserialize, Debug)]
pub struct PaginationToken {
    pub token: Option<String>
}

pub async fn delete_rule_by_id(client: &Client, url_post: &str, token: &str, rule_ids: &str) {
    let response = client
        .post(url_post)
        .bearer_auth(token)
        .body(
        format!(r#"{{
            "delete": {{
              "ids": [
              {}
              ]
              }}
          }}"#,
          rule_ids),
        )
        .header(CONTENT_TYPE, "application/json")
        .send()
        .await
        .unwrap();
    let parsed_response = response.json::<Value>().await;
    println!("{:?} \n", parsed_response.as_ref().unwrap());
}

pub async fn get_response(client: &Client, url: &str, token: &str) -> Response {
        client
        .get(url)
        .bearer_auth(token)
        .header(CONTENT_TYPE, "application/json")
        .send()
        .await
        .unwrap()
}

pub fn parse_and_log_timeline_tweets(parsed_response: &Value, user: &&str, file_path: &String, rule_name: &str) {
    for tweet_meta in parsed_response.get("data").unwrap().as_array().unwrap() {
        let tweet = Tweet {
            data: String::from(tweet_meta.as_object().unwrap().get("text").unwrap().as_str().unwrap()),
            id: String::from(tweet_meta.as_object().unwrap().get("id").unwrap().as_str().unwrap()),
            username: user.to_string(),
            time: String::from(tweet_meta.as_object().unwrap().get("created_at").unwrap().as_str().unwrap()),
            rule_tag: rule_name.to_string()
        };
        write_tweet(&tweet, file_path);
    }
}
