package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	_ "dearearthpb/migrations"

	"cloud.google.com/go/vertexai/genai"
	"github.com/labstack/echo/v5"
	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/models"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"
	"golang.org/x/oauth2/google"
	"google.golang.org/api/option"
)

const REGION = "asia-southeast1"
const MODEL = "gemini-pro"

type ChatRequestChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatRequestSubmission struct {
	Caption string `json:"caption"`
}

type ChatRequest struct {
	Topic      string                   `json:"topic"`
	History    []ChatRequestChatMessage `json:"history"`
	Submission ChatRequestSubmission    `json:"submission"`
}

type ChatResponse struct {
	Content   string `json:"content"`
	AwardedXp int    `json:"awardedXp"`
	AwardedAp int    `json:"awardedAp"`
}

type JournalTopic struct {
	Title   string
	Lead    string
	Starter string
}

func main() {
	ctx := context.Background()
	r := rand.New(rand.NewSource(time.Now().UnixNano()))

	gcreds, err := loadGoogleCredentials(ctx)

	client, err := genai.NewClient(ctx, gcreds.ProjectID, REGION, option.WithCredentials(gcreds))
	if err != nil {
		log.Fatal(err)
	}

	model := client.GenerativeModel(MODEL)
	model.SetCandidateCount(1)
	model.SafetySettings = append(model.SafetySettings, &genai.SafetySetting{
		Category:  genai.HarmCategoryDangerousContent,
		Threshold: genai.HarmBlockNone,
	})
	model.SetMaxOutputTokens(1024)
	model.SetTemperature(0.4)
	model.SetTopP(1)

	app := pocketbase.New()

	app.OnRecordAfterAuthWithOAuth2Request("users").Add(func(e *core.RecordAuthWithOAuth2Event) error {
		name := e.Record.Get("name")
		avatarUrl := e.Record.Get("avatarUrl")
		if name == nil || name == "" {
			e.Record.Set("name", e.OAuth2User.Name)
		}
		if avatarUrl == nil || avatarUrl == "" {
			e.Record.Set("avatarUrl", e.OAuth2User.AvatarUrl)
		}
		return app.Dao().SaveRecord(e.Record)
	})

	app.OnBeforeServe().Add(func(e *core.ServeEvent) error {
		e.Router.POST("/api/dearearth/chat", func(c echo.Context) error {

			var data ChatRequest
			err := json.NewDecoder(c.Request().Body).Decode(&data)
			if err != nil || len(data.History) == 0 {
				return c.NoContent(http.StatusBadRequest)
			}
			for _, msg := range data.History {
				if msg.Role != "USER" && msg.Role != "MODEL" {
					return c.JSON(http.StatusBadRequest, "roles must be either USER or MODEL")
				}
			}

			topicRecord := models.Record{}
			err = app.Dao().
				RecordQuery("journal_topics").
				Select("title", "lead", "starter").
				AndWhere(dbx.HashExp{"title": data.Topic}).
				Limit(1).
				Build().
				One(&topicRecord)
			if err != nil {
				app.Logger().Debug(err.Error())
				return c.JSON(http.StatusNotFound, "Topic not found")
			}

			topic := parseTopic(topicRecord)
			initialPrompt := constructInitialPrompt(topic, data.History[0].Content)

			userRecord, _ := c.Get(apis.ContextAuthRecordKey).(*models.Record)
			awardedXp := 0
			if r.Intn(2) == 1 {
				awardedXp = r.Intn(5) + 1
				app.Logger().Info("Awarded XP", "awardedXp", strconv.Itoa(awardedXp), "recipient", userRecord.Id)
			}
			userRecord.Set("experiencePoints", userRecord.GetInt("experiencePoints")+awardedXp)
			app.Dao().SaveRecord(userRecord)

			chat := model.StartChat()
			isFirstMessage := len(data.History) == 1
			if isFirstMessage {
				modelResponse, err := chat.SendMessage(c.Request().Context(), genai.Text(initialPrompt))
				if err != nil {
					app.Logger().Error(err.Error())
					return c.NoContent(http.StatusInternalServerError)
				}
				return c.JSON(http.StatusOK, ChatResponse{
					Content:   string(modelResponse.Candidates[0].Content.Parts[0].(genai.Text)),
					AwardedXp: awardedXp,
					AwardedAp: 0,
				})
			} else {

				history := []*genai.Content{}

				history = append(history, &genai.Content{
					Role: "USER",
					Parts: []genai.Part{
						genai.Text(initialPrompt),
					},
				})

				for i := 1; i < len(data.History)-1; i++ {
					content := data.History[i].toContent()
					history = append(history, &content)
				}
				chat.History = append(chat.History, history...)

				last := data.History[len(data.History)-1]
				if last.Role != "USER" {
					return c.JSON(http.StatusBadRequest, "Final message must be from role USER")
				}

				response, err := chat.SendMessage(c.Request().Context(), genai.Text(last.Content))
				if err != nil {
					app.Logger().Error(err.Error())
					return c.NoContent(http.StatusInternalServerError)
				}
				responseText := response.Candidates[0].Content.Parts[0].(genai.Text)
				return c.JSON(http.StatusOK, ChatResponse{
					Content:   string(responseText),
					AwardedXp: awardedXp,
					AwardedAp: 0,
				})
			}
		}, apis.ActivityLogger(app), apis.RequireRecordAuth())
		return nil
	})

	migratecmd.MustRegister(app, app.RootCmd, migratecmd.Config{
		Automigrate: false,
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

func (self ChatRequestChatMessage) toContent() genai.Content {
	return genai.Content{
		Role:  strings.ToUpper(self.Role),
		Parts: []genai.Part{genai.Text(self.Content)},
	}
}

func parseTopic(rec models.Record) JournalTopic {
	return JournalTopic{
		Title:   rec.GetString("title"),
		Lead:    rec.GetString("lead"),
		Starter: rec.GetString("starter"),
	}
}

func constructInitialPrompt(topic JournalTopic, userResponse string) string {
	return fmt.Sprintf(
		`
        Context: You are a chatbot designed to help people increase their climate literacy. 
        You know a lot about the climate, but mainly what you do is to respond to me and ask relevant questions to encourage me to find out more about the topic and also do some self-reflection about my climate literacy. 
        Remember that your job is to ask me questions to encourage me. You can also suggest action according to the topic, but keep them simple. For example, if the topic is about waste management, then you can ask me to sort today's rubbish.
		For additional context in giving me information, you can ask me in what region or country that I live in. 
        If I respond in a way that seems out of topic, just reply with "sorry, I don't understand what you mean".
		The topic is: "%s".
		Before you reply, attend, think and remember all the instructions set here.
        We are going to have a chat now. 
        You just asked me: "%s". 
        Here's my response: "%s"
    	`,
		topic.Title,
		topic.Starter,
		userResponse,
	)
}

var GCREDS_SCOPES = []string{"https://www.googleapis.com/auth/cloud-platform"}

func loadGoogleCredentials(ctx context.Context) (*google.Credentials, error) {
	if gcredsB64, present := os.LookupEnv("GCREDS_B64"); present {
		decoded, err := base64.StdEncoding.DecodeString(gcredsB64)
		if err != nil {
			return nil, err
		}

		gcreds, err := google.CredentialsFromJSON(ctx, decoded, GCREDS_SCOPES...)
		if err != nil {
			return nil, err
		}

		return gcreds, nil
	}

	gcredsJson, err := os.ReadFile("gcreds/gcreds.json")
	if err != nil {
		return nil, err
	}

	gcreds, err := google.CredentialsFromJSON(ctx, gcredsJson, GCREDS_SCOPES...)
	if err != nil {
		return nil, err
	}

	return gcreds, nil
}
