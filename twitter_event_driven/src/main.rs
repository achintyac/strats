use dotenv::dotenv;
use serde_json::{Value, Deserializer};
use std::{error::Error, fs::OpenOptions, collections::HashMap, any::type_name};
use reqwest::header::{CONTENT_TYPE};
mod twitter;
mod io;

const POST_RULE: bool = false;
const DELETE_RULE: bool = false;
const GET_RULE: bool = false;
const GET_STREAM: bool = false;
const GET_FULL_HISTORY_FOR_TARGET_USERS: bool = true;

fn type_of<T>(_: T) -> &'static str {
    type_name::<T>()
}

#[tokio::main]
async fn main() {
    dotenv().expect("Failed to read .env file!");

    let config = match envy::from_env::<twitter::TwtrApiConfig>() {
        Ok(config) => config,
        Err(e) => panic!("({:#?})", e),
    };
    let file_path: String = config.file_path;
    let token = config.twitter_bearer_token;
    let url_post = "https://api.twitter.com/2/tweets/search/stream/rules";
    let url_post_stream = "https://api.twitter.com/2/tweets/search/stream/rules";
    let url_get_stream = "https://api.twitter.com/2/tweets/search/stream?tweet.fields=created_at&expansions=author_id&user.fields=created_at";
    let client = reqwest::Client::new();

    if POST_RULE {
        println!("POSTING RULE!");
        let response = client
            .post(url_post)
            // .query("dry_run=false")
            .bearer_auth(&token)
            .body(
                r#"{
                  "add": [
                    {"value": "-is:retweet (from:JumpCryptoHQ OR from:zhusu OR from:CanteringClark OR from:SBF_FTX OR from:JackNiewold OR from:chinterss)",
                    "tag": "crypto baddies"}
                  ]
                }"#,
            )
            .header(CONTENT_TYPE, "application/json")
            .send()
            .await
            .unwrap();

        let parsed_response = response.json::<Value>().await;
        println!("{:?} \n", parsed_response.as_ref().unwrap());
    };

    if DELETE_RULE {
        println!("DELETING A RULE!");
        twitter::delete_rule_by_id(&client,
                            url_post_stream,
                            &token,
                            "1499104156132397056") // can be list of ids: "23145535413, 12351243541,..."
                            .await;
    };

    if GET_RULE {
        println!("GETTING POSTED RULES!");
        let response = twitter::get_response(&client,
                                    url_post_stream,
                                    &token)
                                    .await;
        let parsed_response = response.json::<Value>().await;
        println!("{:?} \n", parsed_response.as_ref().unwrap());
    };

    if GET_FULL_HISTORY_FOR_TARGET_USERS {
        println!("GETTING FULL TWEET HISTORY FOR TARGET USERS!");
        let mut user_ids: HashMap<String, twitter::User> = HashMap::new();
        // let target_users = ["JumpCryptoHQ", "zhusu", "CanteringClark", "SBF_FTX", "JackNiewold", "chinterss"];
        let target_users = ["chinterss"];

        for user in target_users {
            let response = twitter::get_response(&client,
                                        &format!("https://api.twitter.com/2/users/by?usernames={}", user)[..],
                                        &token)
                                        .await;
            let parsed_response = response.json::<Value>().await;
            println!("type of parsed response {:?}", type_of(&parsed_response));

            for user_meta_data in parsed_response {
                user_ids.insert(
                    user_meta_data.get("data").unwrap()[0].get("username").unwrap().as_str().unwrap().to_string(),
                    twitter::User {
                        user_id: user_meta_data.get("data").unwrap()[0].get("id").unwrap().as_str().unwrap().to_string(),
                        screen_name: user_meta_data.get("data").unwrap()[0].get("name").unwrap().as_str().unwrap().to_string()
                        }
                );
            }

            let response = twitter::get_response(&client,
                                        &format!("https://api.twitter.com/2/users/{}/tweets?tweet.fields=created_at&expansions=author_id&user.fields=created_at&max_results=100", user_ids.get(user).unwrap().user_id)[..],
                                        &token)
                                        .await;
            let parsed_response = response.json::<Value>().await;
            println!("this is the data {:?} \n", &parsed_response.as_ref().unwrap().get("data").unwrap().as_array().unwrap());
            twitter::parse_and_log_timeline_tweets(parsed_response.as_ref().unwrap(), &user, &config.file_path_hist, "timeline user pull");


            if let Some(next_token) = &parsed_response.as_ref().unwrap().get("meta").unwrap().get("next_token") {
                let mut pagination_token = twitter::PaginationToken{token: Some(next_token.as_str().unwrap().to_string())};
                // println!("{:?}", &pagination_token);

                loop {
                    let response = twitter::get_response(&client,
                                                &format!("https://api.twitter.com/2/users/{}/tweets?tweet.fields=created_at&expansions=author_id&user.fields=created_at&max_results=100&pagination_token={}",
                                                user_ids.get(user).unwrap().user_id,
                                                &pagination_token.token.unwrap()),
                                                &token)
                                                .await;
                    let parsed_response = response.json::<Value>().await;
                    println!("{:?} \n", &parsed_response);

                    if let Some(next_token) = &parsed_response.as_ref().unwrap().get("meta").unwrap().get("next_token") {
                        // println!("this is the next token {:?}", next_token);
                        pagination_token.token = Some(next_token.as_str().unwrap().to_string());
                        twitter::parse_and_log_timeline_tweets(parsed_response.as_ref().unwrap(), &user, &config.file_path_hist, "timeline user pull");
                        continue;
                    } else {
                        break;
                    }
                }
            }

        }
        println!("\n user id hashmap {:?}", user_ids);
    }

    if GET_STREAM {
        println!("Getting Tweet stream!");
        let mut listen = twitter::get_response(&client,
                                    url_get_stream,
                                    &token)
                                    .await;

        while let Some(chunk) = listen.chunk().await.unwrap() {
            // let parsed_response = serde_json::from_slice::<Value>(&chunk);
            let parsed_response = Deserializer::from_slice(&chunk).into_iter::<Value>();

            for value in parsed_response {
                let mut tweet_meta = match value {
                    Ok(value) => value,
                    Err(_) => {
                        println!("Error in stream.");
                        continue
                    },
                };
                let tweet = twitter::Tweet {
                    data: String::from(tweet_meta.as_object_mut().unwrap().get_mut("data").unwrap().get("text").unwrap().as_str().unwrap()),
                    id: String::from(tweet_meta.as_object_mut().unwrap().get_mut("data").unwrap().get("id").unwrap().as_str().unwrap()),
                    username: String::from(tweet_meta.as_object_mut().unwrap().get_mut("includes").unwrap().get("users").unwrap()[0].get("username").unwrap().as_str().unwrap()),
                    time: String::from(tweet_meta.as_object_mut().unwrap().get_mut("includes").unwrap().get("users").unwrap()[0].get("created_at").unwrap().as_str().unwrap()),
                    rule_tag: String::from(tweet_meta.as_object_mut().unwrap().get_mut("matching_rules").unwrap()[0].get("tag").unwrap().as_str().unwrap()),
                };
                io::write_tweet(&tweet, &file_path);
                println!("{:?}", tweet);
            }
        };
    };
}
